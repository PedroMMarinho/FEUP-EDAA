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
        
        for (int i = 0; i < num_pixels; ++i) {
            Color c = {pixels[i*3], pixels[i*3+1], pixels[i*3+2]};
            int mapped_index = quantizer.getMappedIndex(c);
            
            pixels[i*3]     = palette[mapped_index].r;
            pixels[i*3+1]   = palette[mapped_index].g;
            pixels[i*3+2]   = palette[mapped_index].b;
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
}