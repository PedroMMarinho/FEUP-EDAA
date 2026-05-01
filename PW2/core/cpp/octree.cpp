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
#include <chrono>
#if defined(_WIN32) || defined(_WIN64)
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

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
    void collectLeaves(OctreeNode* node, std::vector<Color>& out) {
        if (!node) return;
        if (node->isLeaf) {
            out.push_back({
                (int)(node->sumR / node->colorCount),
                (int)(node->sumG / node->colorCount),
                (int)(node->sumB / node->colorCount)
            });
        } else {
            for (int i = 0; i < 8; ++i) collectLeaves(node->children[i], out);
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

    std::vector<Color> getKColors() {
        std::vector<Color> out;
        collectLeaves(root, out);
        return out;
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

// Global palette and frame info for live quantization
static std::vector<int> g_pal_flat;
static int g_pal_size = 0;
static int g_frame_count = 0;
static int g_refresh_every = 30; 

// For accerola shadder
static const int bayer8[8 * 8] = {
    0, 32, 8, 40, 2, 34, 10, 42,
    48, 16, 56, 24, 50, 18, 58, 26,  
    12, 44,  4, 36, 14, 46,  6, 38, 
    60, 28, 52, 20, 62, 30, 54, 22,  
    3, 35, 11, 43,  1, 33,  9, 41,  
    51, 19, 59, 27, 49, 17, 57, 25, 
    15, 47,  7, 39, 13, 45,  5, 37, 
    63, 31, 55, 23, 61, 29, 53, 21
};


extern "C" {
    // Accerola Shader
    // MODE 1: UNIFORM RGB (No Palette Provided)
    // Calculates nearest colors mathematically per-channel.
    EXPORT void acerola_dither_uniform(uint8_t* pixels, int width, int height, int steps_per_channel, float spread) {
        if (steps_per_channel < 2) steps_per_channel = 2;
        float step_factor = steps_per_channel - 1.0f;

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int idx = (y * width + x) * 3;

                // Step 1: Get the dither noise value for this specific screen coordinate.
                // We divide by 64.0f to normalize the matrix [0 to 63] down to [0.0 to 1.0].
                // We subtract 0.5f to center the noise around 0 [-0.5 to 0.5].
                int bayer_idx = (x % 8) + (y % 8) * 8;
                float bayer_val = (bayer8[bayer_idx] / 64.0f) - 0.5f;

                // Process Red, Green, and Blue independently
                for (int c = 0; c < 3; c++) {
                    float color = pixels[idx + c] / 255.0f;     // Normalize to [0.0, 1.0]
                    color += spread * bayer_val;                // Step 2: Add dither noise
                    
                    if (color < 0.0f) color = 0.0f;             // Clamp limits
                    if (color > 1.0f) color = 1.0f;

                    // Step 3: Compress the color palette (Quantization)
                    // Multiply by steps, round to nearest integer, divide by steps.
                    float quantized = std::floor(step_factor * color + 0.5f) / step_factor;

                    pixels[idx + c] = static_cast<uint8_t>(quantized * 255.0f); // Map back to 0-255
                }
            }
        }
    }

    // MODE 2: CUSTOM PALETTE (Palette Provided)
    // Maps grayscale luminance to a 1D color palette array.
    EXPORT void acerola_dither_palette(uint8_t* pixels, int width, int height, uint8_t* palette, int palette_size, float spread) {
        if (palette_size < 2) return; 

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int idx = (y * width + x) * 3;

                // Step 1: Get dither noise
                int bayer_idx = (x % 8) + (y % 8) * 8;
                float bayer_val = (bayer8[bayer_idx] / 64.0f) - 0.5f;

                // Step 2: Convert RGB to Grayscale (Luminance)
                float r = pixels[idx] / 255.0f;
                float g = pixels[idx + 1] / 255.0f;
                float b = pixels[idx + 2] / 255.0f;
                float luminance = (0.299f * r) + (0.587f * g) + (0.114f * b);

                // Step 3: Add dither noise to the grayscale value
                luminance += spread * bayer_val;

                if (luminance < 0.0f) luminance = 0.0f;
                if (luminance > 1.0f) luminance = 1.0f;

                // Step 4: Map the noisy grayscale value to a palette index
                // A luminance of 0.0 picks the first color, 1.0 picks the last color.
                int palette_index = static_cast<int>(std::round(luminance * (palette_size - 1)));

                // Safety bounds check
                if (palette_index < 0) palette_index = 0;
                if (palette_index >= palette_size) palette_index = palette_size - 1;

                // Step 5: Overwrite the pixel with the chosen color from the palette
                int pal_idx = palette_index * 3;
                pixels[idx]     = palette[pal_idx];
                pixels[idx + 1] = palette[pal_idx + 1];
                pixels[idx + 2] = palette[pal_idx + 2];
            }
        }
    }
    // Use for custom pallet extraction
    EXPORT int extract_octree_palette(uint8_t* pixels, int width, int height, int maxColors, uint8_t* out_palette) {
        OctreeQuantizer octree(maxColors);
        int total_pixels = width * height;
        
        for (int i = 0; i < total_pixels; i++) {
            Color c = { pixels[i * 3], pixels[i * 3 + 1], pixels[i * 3 + 2] };
            octree.addColor(c);
        }

        std::vector<Color> palette = octree.getPalette();
        int actual_colors = palette.size();

        for (int i = 0; i < actual_colors; i++) {
            out_palette[i * 3]     = palette[i].r;
            out_palette[i * 3 + 1] = palette[i].g;
            out_palette[i * 3 + 2] = palette[i].b;
        }

        return actual_colors;
    }
    


    // Live Quantization #
    EXPORT void build_octree_palette(unsigned char* pixels, int num_pixels, int max_colors) {
        OctreeQuantizer quantizer(max_colors);
        for (int i = 0; i < num_pixels; ++i)
            quantizer.addColor({pixels[i*3], pixels[i*3+1], pixels[i*3+2]});

        std::vector<Color> palette = quantizer.getPalette();
        g_pal_size = (int)palette.size();
        g_pal_flat.resize(g_pal_size * 3);
        for (int j = 0; j < g_pal_size; ++j) {
            g_pal_flat[j*3]   = palette[j].r;
            g_pal_flat[j*3+1] = palette[j].g;
            g_pal_flat[j*3+2] = palette[j].b;
        }
    }

   EXPORT void apply_palette(unsigned char* pixels, int num_pixels) {
        int P = g_pal_size;
        const int* pal = g_pal_flat.data();
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < num_pixels; ++i) {
            int pr = pixels[i*3], pg = pixels[i*3+1], pb = pixels[i*3+2];
            int best = 0, bestD = INT32_MAX;
            for (int j = 0; j < P; ++j) {
                int dr = pr - pal[j*3];
                int dg = pg - pal[j*3+1];
                int db = pb - pal[j*3+2];
                int d  = dr*dr + dg*dg + db*db;
                if (d < bestD) { bestD = d; best = j; }
                if (bestD == 0) break;
            }
            pixels[i*3]   = pal[best*3];
            pixels[i*3+1] = pal[best*3+1];
            pixels[i*3+2] = pal[best*3+2];
        }
    }

    EXPORT void octree_quantize_live(unsigned char* pixels, int num_pixels, int max_colors) {
        if (g_pal_size == 0 || g_frame_count % g_refresh_every == 0)
            build_octree_palette(pixels, num_pixels, max_colors);
        apply_palette(pixels, num_pixels);
        g_frame_count++;
    }

    EXPORT void reset_live_palette() {
        g_pal_size = 0;
        g_frame_count = 0;
    }
    // Live Quantization #


    // Baseline Algorithm
    EXPORT void octree_quantize_baseline(unsigned char* pixels, int num_pixels, int max_colors) {
    OctreeQuantizer quantizer(max_colors);
    
    for (int i = 0; i < num_pixels; ++i) {
        Color c = {pixels[i*3], pixels[i*3+1], pixels[i*3+2]};
        quantizer.addColor(c);
    }
    
    std::vector<Color> palette = quantizer.getPalette();
    int P = (int)palette.size();

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
            if (bestD == 0) break; 
        }
        pixels[i*3]   = pal_flat[best*3];
        pixels[i*3+1] = pal_flat[best*3+1];
        pixels[i*3+2] = pal_flat[best*3+2];
    }
}

    // Image info for CSV logging
   EXPORT double calculate_exact_color_difference(const uint8_t* pixels, int num_pixels) {
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
   EXPORT void kmeans_quantize(uint8_t* pixels, int width, int height,
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

   EXPORT void som_quantize(uint8_t* pixels, int width, int height,
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

   EXPORT void som_octree_quantize(uint8_t* pixels, int width, int height,
                            int K, float alpha_winner,
                            float threshold, int subset_size,
                            uint32_t seed)
    {
        int n = width * height;
    
        OctreeQuantizer quantizer(K);
        for (int i = 0; i < n; ++i)
            quantizer.addColor({pixels[i*3], pixels[i*3+1], pixels[i*3+2]});
    
        std::vector<Color> k_colors = quantizer.getKColors();
        int actual_K = (int)k_colors.size();
    
        // ── Step 2: 2D map layout ─────────────────────────────────────────────────
        int map_cols = (int)std::ceil(std::sqrt((double)actual_K));
        int map_rows = (int)std::ceil((double)actual_K / map_cols);
        int map_size = map_rows * map_cols;
    
        std::vector<float> weights(map_size * 3, 128.0f);  
        for (int i = 0; i < actual_K; ++i) {
            weights[i*3+0] = (float)k_colors[i].r;
            weights[i*3+1] = (float)k_colors[i].g;
            weights[i*3+2] = (float)k_colors[i].b;
        }
    
        std::vector<float> data(n * 3);
        for (int i = 0; i < n * 3; ++i) data[i] = (float)pixels[i];
    
        std::mt19937 rng(seed);
        int N_prime = (subset_size > 0) ? std::min(subset_size, n) : n;
    
        std::vector<int> indices(n);
        std::iota(indices.begin(), indices.end(), 0);
    
        int t = 1;
        while (true) {
            float alpha_w = alpha_winner / (float)t;
            float alpha_n = alpha_w / 100.0f;
    
            std::shuffle(indices.begin(), indices.end(), rng);
    
            float total_delta = 0.0f;
    
            for (int s = 0; s < N_prime; ++s) {
                int pi = indices[s];
                float px_r = data[pi*3+0];
                float px_g = data[pi*3+1];
                float px_b = data[pi*3+2];
    
                int winner = 0;
                float best = std::numeric_limits<float>::max();
                for (int j = 0; j < map_size; ++j) {
                    float dr = px_r - weights[j*3+0];
                    float dg = px_g - weights[j*3+1];
                    float db = px_b - weights[j*3+2];
                    float d  = dr*dr + dg*dg + db*db;
                    if (d < best) { best = d; winner = j; }
                }
    
                int wr = winner / map_cols;
                int wc = winner % map_cols;
    
                for (int j = 0; j < map_size; ++j) {
                    int jr = j / map_cols;
                    int jc = j % map_cols;
                    int dr = jr - wr;
                    int dc = jc - wc;
                    int dist2 = dr*dr + dc*dc;
    
                    float alpha = (dist2 == 0) ? alpha_w :
                                (dist2 <= 2) ? alpha_n : 0.0f;
                    if (alpha == 0.0f) continue;
    
                    float dw0 = alpha * (px_r - weights[j*3+0]);
                    float dw1 = alpha * (px_g - weights[j*3+1]);
                    float dw2 = alpha * (px_b - weights[j*3+2]);
    
                    weights[j*3+0] += dw0;
                    weights[j*3+1] += dw1;
                    weights[j*3+2] += dw2;
    
                    total_delta += std::fabs(dw0) + std::fabs(dw1) + std::fabs(dw2);
                }
            }
    
            float avg_delta = total_delta / (float)(N_prime * map_size * 3);
            if (avg_delta < threshold) break;
    
            t++;
        }
    
        std::vector<uint8_t> palette(map_size * 3);
        for (int j = 0; j < map_size; ++j) {
            palette[j*3+0] = (uint8_t)std::fmin(255.f, std::fmax(0.f, weights[j*3+0] + 0.5f));
            palette[j*3+1] = (uint8_t)std::fmin(255.f, std::fmax(0.f, weights[j*3+1] + 0.5f));
            palette[j*3+2] = (uint8_t)std::fmin(255.f, std::fmax(0.f, weights[j*3+2] + 0.5f));
        }
    
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < n; ++i) {
            float r = data[i*3+0];
            float g = data[i*3+1];
            float b = data[i*3+2];
    
            int best_j = 0;
            float best_d = std::numeric_limits<float>::max();
            for (int j = 0; j < map_size; ++j) {
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

} // extern "C"