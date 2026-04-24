#include <iostream>
#include <vector>
#include <array>
#include <memory>
#include <vector>
#include <cstdint>
#include <cstring>
#include <unordered_map>
#include <cassert>
#include <algorithm> 
#include <cmath>   
#include <numeric>
#include <limits>
#include <random>

struct Color {
    int r, g, b;
};

struct OctreeNode {
    bool isLeaf = false;
    int level = 0;
    int colorCount = 0;
    
    long long sumR = 0, sumG = 0, sumB = 0; 
    
    int colorIndex = -1;
    std::array<OctreeNode*, 8> children{nullptr};
    
    OctreeNode* nextNode = nullptr;

    ~OctreeNode() {
        for (auto child : children) {
            delete child;
        }
    }
};

class OctreeQuantizer {
private:
    int maxColors;
    int leafCount = 0;
    OctreeNode* root = nullptr;
    
    std::array<OctreeNode*, 8> reduceList{nullptr}; 

    int getBranch(const Color& color, int depth) {
        int shift = 7 - depth;
        int r = (color.r >> shift) & 1;
        int g = (color.g >> shift) & 1;
        int b = (color.b >> shift) & 1;
        return (r << 2) | (g << 1) | b;
    }

    void insertTree(OctreeNode*& node, const Color& color, int depth) {
        if (!node) {
            node = new OctreeNode();
            node->level = depth;
            
            if (depth == 8) {
                node->isLeaf = true;
                leafCount++;
            } else {
                node->nextNode = reduceList[depth];
                reduceList[depth] = node;
            }
        }

        if (node->isLeaf) {
            node->colorCount++;
            node->sumR += color.r;
            node->sumG += color.g;
            node->sumB += color.b;
        } else {
            int branch = getBranch(color, depth);
            insertTree(node->children[branch], color, depth + 1);
        }
    }

    void reduceTree() {
        int d = 7;
        while (d >= 0 && reduceList[d] == nullptr) {
            d--;
        }
        if (d < 0) return;

        OctreeNode* node = reduceList[d];
        reduceList[d] = node->nextNode;

        int childrenCount = 0;
        for (int i = 0; i < 8; ++i) {
            if (node->children[i]) {
                node->sumR += node->children[i]->sumR;
                node->sumG += node->children[i]->sumG;
                node->sumB += node->children[i]->sumB;
                node->colorCount += node->children[i]->colorCount;
                
                delete node->children[i];
                node->children[i] = nullptr;
                childrenCount++;
            }
        }
        
        node->isLeaf = true;
        leafCount -= (childrenCount - 1);
    }

    void buildColorTable(OctreeNode* node, std::vector<Color>& palette) {
        if (!node) return;
        
        if (node->isLeaf) {
            node->colorIndex = palette.size();
            palette.push_back({
                static_cast<int>(node->sumR / node->colorCount),
                static_cast<int>(node->sumG / node->colorCount),
                static_cast<int>(node->sumB / node->colorCount)
            });
        } else {
            for (int i = 0; i < 8; ++i) {
                buildColorTable(node->children[i], palette);
            }
        }
    }

    int quantizeColor(OctreeNode* node, const Color& color, int depth) {
        if (!node) return 0;
        if (node->isLeaf) return node->colorIndex;
        
        int branch = getBranch(color, depth);
        if (node->children[branch]) {
            return quantizeColor(node->children[branch], color, depth + 1);
        }
        
        return 0; 
    }
    void collectLeaves(OctreeNode* node, std::vector<std::pair<Color,int>>& leaves) {
        if (!node) return;
        if (node->isLeaf) {
            Color c = {
                (int)(node->sumR / node->colorCount),
                (int)(node->sumG / node->colorCount),
                (int)(node->sumB / node->colorCount)
            };
            leaves.push_back({c, node->colorCount});
        } else {
            for (int i = 0; i < 8; ++i)
                collectLeaves(node->children[i], leaves);
        }
    }

public:
    OctreeQuantizer(int maxColors) : maxColors(maxColors) {}

    ~OctreeQuantizer() {
        delete root;
    }

    void addColor(const Color& color) {
        insertTree(root, color, 0);
        
        while (leafCount > maxColors) {
            reduceTree();
        }
    }

    std::vector<std::pair<Color,int>> getWeightedPalette() {
        std::vector<std::pair<Color,int>> leaves;
        collectLeaves(root, leaves);
        return leaves;
    }

    std::vector<Color> getPalette() {
        std::vector<Color> palette;
        buildColorTable(root, palette);
        return palette;
    }

    int getMappedIndex(const Color& color) {
        return quantizeColor(root, color, 0);
    }
};

extern "C" {
    // Baseline Algorithm
    void octree_quantize_baseline(unsigned char* pixels, int num_pixels, int max_colors) {
    OctreeQuantizer quantizer(max_colors);
    
    for (int i = 0; i < num_pixels; ++i) {
        Color c = {pixels[i*3], pixels[i*3+1], pixels[i*3+2]};
        quantizer.addColor(c);
    }
    
    std::vector<Color> palette = quantizer.getPalette();
    int P = (int)palette.size();

    // Flat array for better cache locality
    std::vector<int> pal_flat(P * 3);
    for (int j = 0; j < P; ++j) {
        pal_flat[j*3]   = palette[j].r;
        pal_flat[j*3+1] = palette[j].g;
        pal_flat[j*3+2] = palette[j].b;
    }

    #pragma omp parallel for schedule(static)
    for (int i = 0; i < num_pixels; ++i) {
        int pr = pixels[i*3], pg = pixels[i*3+1], pb = pixels[i*3+2];
        int best = 0, bestD = INT32_MAX;
        for (int j = 0; j < P; ++j) {
            int dr = pr - pal_flat[j*3];
            int dg = pg - pal_flat[j*3+1];
            int db = pb - pal_flat[j*3+2];
            int d  = dr*dr + dg*dg + db*db;
            if (d < bestD) { bestD = d; best = j; }
            if (bestD == 0) break;  // early exit on perfect match
        }
        pixels[i*3]   = pal_flat[best*3];
        pixels[i*3+1] = pal_flat[best*3+1];
        pixels[i*3+2] = pal_flat[best*3+2];
    }
}

    // Image info for CSV logging
    double calculate_exact_color_difference(const uint8_t* pixels, int num_pixels) {
        std::vector<uint32_t> colors;
        colors.reserve(num_pixels);
        for (int i = 0; i < num_pixels; ++i) {
            uint32_t r = pixels[i * 3];
            uint32_t g = pixels[i * 3 + 1];
            uint32_t b = pixels[i * 3 + 2];
            colors.push_back((r << 16) | (g << 8) | b);
        }

        std::sort(colors.begin(), colors.end());
        auto last = std::unique(colors.begin(), colors.end());
        colors.erase(last, colors.end());

        long long N = colors.size();
        if (N < 2) return 0.0;

        double total_distance = 0.0;

        #pragma omp parallel for reduction(+:total_distance) schedule(dynamic)
        for (long long i = 0; i < N; ++i) {
            double local_sum = 0.0;
            uint32_t c1 = colors[i];
            int r1 = (c1 >> 16) & 0xFF;
            int g1 = (c1 >> 8) & 0xFF;
            int b1 = c1 & 0xFF;

            for (long long j = 0; j < N; ++j) {
                uint32_t c2 = colors[j];
                int dr = r1 - ((c2 >> 16) & 0xFF);
                int dg = g1 - ((c2 >> 8) & 0xFF);
                int db = b1 - (c2 & 0xFF);

                local_sum += std::sqrt(dr * dr + dg * dg + db * db);
            }
            total_distance += local_sum;
        }

        return total_distance / ((double)(N - 1) * (double)(N - 1));
    }

    // K-Means Algorithm
    void kmeans_quantize(uint8_t* pixels, int width, int height,
                        int k, int max_iter, uint32_t seed)
    {
        int n = width * height;

        std::vector<float> data(n * 3);
        for (int i = 0; i < n * 3; ++i)
            data[i] = (float)pixels[i];

        std::mt19937 rng(seed);
        std::vector<int> perm(n);
        std::iota(perm.begin(), perm.end(), 0);
        std::shuffle(perm.begin(), perm.end(), rng);

        std::vector<float> centroids(k * 3);
        for (int i = 0; i < k; ++i)
            for (int c = 0; c < 3; ++c)
                centroids[i * 3 + c] = data[perm[i] * 3 + c];

        std::vector<int>   labels(n, 0);
        std::vector<float> new_centroids(k * 3);
        std::vector<int>   counts(k);

        for (int iter = 0; iter < max_iter; ++iter) {

            bool changed = false;
            for (int i = 0; i < n; ++i) {
                float best_dist = std::numeric_limits<float>::max();
                int   best_k    = 0;
                for (int j = 0; j < k; ++j) {
                    float dr = data[i*3+0] - centroids[j*3+0];
                    float dg = data[i*3+1] - centroids[j*3+1];
                    float db = data[i*3+2] - centroids[j*3+2];
                    float d  = dr*dr + dg*dg + db*db;
                    if (d < best_dist) { best_dist = d; best_k = j; }
                }
                if (labels[i] != best_k) { labels[i] = best_k; changed = true; }
            }
            if (!changed) break;

            std::fill(new_centroids.begin(), new_centroids.end(), 0.0f);
            std::fill(counts.begin(), counts.end(), 0);
            for (int i = 0; i < n; ++i) {
                int j = labels[i];
                new_centroids[j*3+0] += data[i*3+0];
                new_centroids[j*3+1] += data[i*3+1];
                new_centroids[j*3+2] += data[i*3+2];
                counts[j]++;
            }
            for (int j = 0; j < k; ++j) {
                if (counts[j] > 0) {
                    centroids[j*3+0] = new_centroids[j*3+0] / counts[j];
                    centroids[j*3+1] = new_centroids[j*3+1] / counts[j];
                    centroids[j*3+2] = new_centroids[j*3+2] / counts[j];
                }
            }
        }

        for (int i = 0; i < n; ++i) {
            int j = labels[i];
            pixels[i*3+0] = (uint8_t)(centroids[j*3+0] + 0.5f);
            pixels[i*3+1] = (uint8_t)(centroids[j*3+1] + 0.5f);
            pixels[i*3+2] = (uint8_t)(centroids[j*3+2] + 0.5f);
        }
    }

    void som_quantize(uint8_t* pixels, int width, int height,
                  int K, int max_iter,
                  float lr0, float sigma0, float tol,
                  uint32_t seed)
{
    int n = width * height;
 
    std::vector<float> data(n * 3);
    for (int i = 0; i < n * 3; ++i)
        data[i] = (float)pixels[i];
 
    std::mt19937 rng(seed);
    std::vector<int> perm(n);
    std::iota(perm.begin(), perm.end(), 0);
    std::shuffle(perm.begin(), perm.end(), rng);
 
    std::vector<float> weights(K * 3);
    for (int i = 0; i < K; ++i) {
        weights[i*3+0] = data[perm[i]*3+0];
        weights[i*3+1] = data[perm[i]*3+1];
        weights[i*3+2] = data[perm[i]*3+2];
    }
 
    std::vector<float> pos(K);
    for (int i = 0; i < K; ++i) pos[i] = (float)i;
 
    std::uniform_int_distribution<int> rand_pixel(0, n - 1);
 
    for (int t = 0; t < max_iter; ++t) {
        float progress = (float)t / (float)max_iter;
        float lr    = lr0    * std::exp(-progress * 9.0f);  
        float sigma = sigma0 * std::exp(-progress * 9.0f);
        float sigma2 = 2.0f * sigma * sigma;
 
        int pi = rand_pixel(rng);
        const float sr = data[pi*3+0];
        const float sg = data[pi*3+1];
        const float sb = data[pi*3+2];
 
        int winner = 0;
        float best = std::numeric_limits<float>::max();
        for (int j = 0; j < K; ++j) {
            float dr = sr - weights[j*3+0];
            float dg = sg - weights[j*3+1];
            float db = sb - weights[j*3+2];
            float d  = dr*dr + dg*dg + db*db;
            if (d < best) { best = d; winner = j; }
        }
 
        float total_delta = 0.0f;
        for (int j = 0; j < K; ++j) {
            float diff = pos[j] - (float)winner;
            float h    = std::exp(-(diff * diff) / sigma2);
            float scale = lr * h;
 
            float dr = scale * (sr - weights[j*3+0]);
            float dg = scale * (sg - weights[j*3+1]);
            float db = scale * (sb - weights[j*3+2]);
 
            weights[j*3+0] += dr;
            weights[j*3+1] += dg;
            weights[j*3+2] += db;
 
            total_delta += std::fabs(dr) + std::fabs(dg) + std::fabs(db);
        }
 
        if (total_delta < tol)
            break;
    }
 
    std::vector<uint8_t> palette(K * 3);
    for (int j = 0; j < K; ++j) {
        palette[j*3+0] = (uint8_t)std::fmin(255.0f, std::fmax(0.0f, weights[j*3+0] + 0.5f));
        palette[j*3+1] = (uint8_t)std::fmin(255.0f, std::fmax(0.0f, weights[j*3+1] + 0.5f));
        palette[j*3+2] = (uint8_t)std::fmin(255.0f, std::fmax(0.0f, weights[j*3+2] + 0.5f));
    }
 
    #pragma omp parallel for schedule(static)
    for (int i = 0; i < n; ++i) {
        float r = data[i*3+0];
        float g = data[i*3+1];
        float b = data[i*3+2];
 
        int best_j = 0;
        float best_d = std::numeric_limits<float>::max();
        for (int j = 0; j < K; ++j) {
            float dr = r - weights[j*3+0];
            float dg = g - weights[j*3+1];
            float db = b - weights[j*3+2];
            float d  = dr*dr + dg*dg + db*db;
            if (d < best_d) { best_d = d; best_j = j; }
        }
 
        pixels[i*3+0] = palette[best_j*3+0];
        pixels[i*3+1] = palette[best_j*3+1];
        pixels[i*3+2] = palette[best_j*3+2];
    }
    }

    void som_octree_quantize(uint8_t* pixels, int width, int height,
                         int K, int intermediate,
                         int max_iter, float lr0, float sigma0,
                         float tol, uint32_t seed)
{
    int n = width * height;
 
    OctreeQuantizer quantizer(intermediate);
    for (int i = 0; i < n; ++i)
        quantizer.addColor({pixels[i*3], pixels[i*3+1], pixels[i*3+2]});
 
    std::vector<std::pair<Color,int>> weighted = quantizer.getWeightedPalette();
    int M = (int)weighted.size(); 
 
    std::mt19937 rng(seed);
 
    std::vector<int> sample_pool;
    sample_pool.reserve(M * 10); 
    int total_weight = 0;
    for (auto& [c, cnt] : weighted) total_weight += cnt;
    for (int i = 0; i < M; ++i) {
        int repeats = std::max(1, (int)std::round(10000.0 * weighted[i].second / total_weight));
        for (int r = 0; r < repeats; ++r)
            sample_pool.push_back(i);
    }
    std::shuffle(sample_pool.begin(), sample_pool.end(), rng);
 
    std::vector<int> perm(M);
    std::iota(perm.begin(), perm.end(), 0);
    std::shuffle(perm.begin(), perm.end(), rng);
 
    std::vector<float> weights(K * 3);
    for (int i = 0; i < K; ++i) {
        int idx = perm[i % M];
        weights[i*3+0] = (float)weighted[idx].first.r;
        weights[i*3+1] = (float)weighted[idx].first.g;
        weights[i*3+2] = (float)weighted[idx].first.b;
    }
 
    std::uniform_int_distribution<int> rand_pool(0, (int)sample_pool.size() - 1);
 
    for (int t = 0; t < max_iter; ++t) {
        float progress = (float)t / (float)max_iter;
        float lr    = lr0    * std::exp(-progress * 9.0f);  
        float sigma = sigma0 * std::exp(-progress * 9.0f);
        float sigma2 = 2.0f * sigma * sigma;
 
        int ci = sample_pool[rand_pool(rng)];
        float sr = (float)weighted[ci].first.r;
        float sg = (float)weighted[ci].first.g;
        float sb = (float)weighted[ci].first.b;
 
        int winner = 0;
        float best = std::numeric_limits<float>::max();
        for (int j = 0; j < K; ++j) {
            float dr = sr - weights[j*3+0];
            float dg = sg - weights[j*3+1];
            float db = sb - weights[j*3+2];
            float d  = dr*dr + dg*dg + db*db;
            if (d < best) { best = d; winner = j; }
        }
 
        float total_delta = 0.0f;
        for (int j = 0; j < K; ++j) {
            float diff = (float)(j - winner);
            float h    = std::exp(-(diff * diff) / sigma2);
            float scale = lr * h;
 
            float dr = scale * (sr - weights[j*3+0]);
            float dg = scale * (sg - weights[j*3+1]);
            float db = scale * (sb - weights[j*3+2]);
 
            weights[j*3+0] += dr;
            weights[j*3+1] += dg;
            weights[j*3+2] += db;
 
            total_delta += std::fabs(dr) + std::fabs(dg) + std::fabs(db);
        }
 
        if (total_delta < tol) break;
    }
 
    std::vector<uint8_t> palette(K * 3);
    for (int j = 0; j < K; ++j) {
        palette[j*3+0] = (uint8_t)std::fmin(255.f, std::fmax(0.f, weights[j*3+0] + 0.5f));
        palette[j*3+1] = (uint8_t)std::fmin(255.f, std::fmax(0.f, weights[j*3+1] + 0.5f));
        palette[j*3+2] = (uint8_t)std::fmin(255.f, std::fmax(0.f, weights[j*3+2] + 0.5f));
    }
 
    #pragma omp parallel for schedule(static)
    for (int i = 0; i < n; ++i) {
        float r = (float)pixels[i*3+0];
        float g = (float)pixels[i*3+1];
        float b = (float)pixels[i*3+2];
 
        int best_j = 0;
        float best_d = std::numeric_limits<float>::max();
        for (int j = 0; j < K; ++j) {
            float dr = r - weights[j*3+0];
            float dg = g - weights[j*3+1];
            float db = b - weights[j*3+2];
            float d  = dr*dr + dg*dg + db*db;
            if (d < best_d) { best_d = d; best_j = j; }
        }
 
        pixels[i*3+0] = palette[best_j*3+0];
        pixels[i*3+1] = palette[best_j*3+1];
        pixels[i*3+2] = palette[best_j*3+2];
    }
}
}