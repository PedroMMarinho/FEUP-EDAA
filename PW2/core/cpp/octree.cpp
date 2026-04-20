#include <vector>
#include <cstdint>
#include <iostream>

struct Node {
    bool is_leaf;
    int level;
    uint64_t pixel_count;
    uint64_t red_sum;
    uint64_t green_sum;
    uint64_t blue_sum;
    Node* children[8];

    Node(int lvl) : is_leaf(false), level(lvl), pixel_count(0), 
                    red_sum(0), green_sum(0), blue_sum(0) {
        for(int i = 0; i < 8; ++i) children[i] = nullptr;
    }

    int get_color_index(uint8_t r, uint8_t g, uint8_t b) {
        int shift = 7 - level;
        int bit_r = (r >> shift) & 1;
        int bit_g = (g >> shift) & 1;
        int bit_b = (b >> shift) & 1;
        return (bit_r << 2) | (bit_g << 1) | bit_b;
    }

    void get_avg_color(uint8_t &out_r, uint8_t &out_g, uint8_t &out_b) {
        if (pixel_count == 0) { out_r=0; out_g=0; out_b=0; return; }
        out_r = red_sum / pixel_count;
        out_g = green_sum / pixel_count;
        out_b = blue_sum / pixel_count;
    }
};

class Octree {
public:
    int max_depth;
    Node* root;
    int leaf_count;
    std::vector<std::vector<Node*>> reducible_nodes;

    Octree(int depth = 8) : max_depth(depth), leaf_count(0) {
        root = new Node(0);
        reducible_nodes.resize(max_depth);
    }

    ~Octree() { destroy_tree(root); }
    void destroy_tree(Node* node) {
        if (!node) return;
        for (int i=0; i<8; ++i) destroy_tree(node->children[i]);
        delete node;
    }

    void insert(uint8_t r, uint8_t g, uint8_t b) {
        Node* node = root;
        node->pixel_count++;

        for (int depth = 0; depth < max_depth; ++depth) {
            int index = node->get_color_index(r, g, b);

            if (node->children[index] == nullptr) {
                Node* child = new Node(depth + 1);
                node->children[index] = child;

                if (depth + 1 == max_depth) {
                    child->is_leaf = true;
                    leaf_count++;
                } else {
                    reducible_nodes[depth + 1].push_back(child);
                }
            }
            node = node->children[index];
            if (node->is_leaf) break;
        }
        node->red_sum += r;
        node->green_sum += g;
        node->blue_sum += b;
        node->pixel_count++;
    }

    bool reduce_tree() {
        for (int level = max_depth - 1; level > 0; --level) {
            if (!reducible_nodes[level].empty()) {
                Node* node = reducible_nodes[level].back();
                reducible_nodes[level].pop_back();

                int leaf_children = 0;
                for (int i = 0; i < 8; ++i) {
                    Node* child = node->children[i];
                    if (child != nullptr && child->is_leaf) {
                        node->red_sum   += child->red_sum;
                        node->green_sum += child->green_sum;
                        node->blue_sum  += child->blue_sum;
                        node->pixel_count += child->pixel_count;
                        
                        delete child; 
                        node->children[i] = nullptr;
                        leaf_children++;
                    }
                }
                node->is_leaf = true;
                leaf_count -= (leaf_children - 1);
                
                return true;
            }
        }
        return false;
    }

    void get_mapped_color(uint8_t r, uint8_t g, uint8_t b, uint8_t &out_r, uint8_t &out_g, uint8_t &out_b) {
        Node* node = root;
        for (int i = 0; i < max_depth; ++i) {
            if (node->is_leaf) break;
            int index = node->get_color_index(r, g, b);
            Node* child = node->children[index];
            if (child == nullptr) break;
            node = child;
        }
        node->get_avg_color(out_r, out_g, out_b);
    }
};


extern "C" {
    // First Algorithm: Baseline Octree Quantization
    void octree_quantize_baseline(uint8_t* pixels, int num_pixels, int target_colors) {
        Octree tree(8);

        for(int i = 0; i < num_pixels; ++i) {
            tree.insert(pixels[i*3], pixels[i*3+1], pixels[i*3+2]);
            
            while(tree.leaf_count > target_colors) {
                if (!tree.reduce_tree()) break; 
            }
        }

        while(tree.leaf_count > target_colors) {
            if (!tree.reduce_tree()) break;
        }

        for(int i = 0; i < num_pixels; ++i) {
            uint8_t r, g, b;
            tree.get_mapped_color(pixels[i*3], pixels[i*3+1], pixels[i*3+2], r, g, b);
            pixels[i*3] = r;
            pixels[i*3+1] = g;
            pixels[i*3+2] = b;
        }
    }
    // Second Algorithm:
}