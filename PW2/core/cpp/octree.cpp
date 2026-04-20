#include <vector>
#include <cstdint>
#include <cstring>
#include <unordered_map>
#include <cassert>

template<typename T, size_t BlockSize = 4096>
class PoolAllocator {
    struct Block {
        alignas(T) char data[sizeof(T) * BlockSize];
        size_t used = 0;
        Block* next = nullptr;
    };

    Block* head;
    Block* current;

    void add_block() {
        Block* b = new Block();
        b->next = nullptr;
        if (!head) head = b;
        if (current) current->next = b;
        current = b;
    }

public:
    PoolAllocator() : head(nullptr), current(nullptr) { add_block(); }

    ~PoolAllocator() {
        Block* b = head;
        while (b) {
            Block* next = b->next;
            delete b;
            b = next;
        }
    }

    T* allocate() {
        if (current->used >= BlockSize) add_block();
        T* obj = reinterpret_cast<T*>(current->data) + current->used;
        current->used++;
        return obj;
    }
};


struct Node {
    uint64_t red_sum   = 0;
    uint64_t green_sum = 0;
    uint64_t blue_sum  = 0;
    uint32_t pixel_count = 0;

    // Singly-linked list of reducible nodes at each level.
    Node* next_reducible = nullptr;

    Node* children[8] = {};

    bool is_leaf = false;
    bool is_dead = false;

    inline int color_index(uint8_t r, uint8_t g, uint8_t b, int shift) const {
        return (((r >> shift) & 1) << 2)
             | (((g >> shift) & 1) << 1)
             |  ((b >> shift) & 1);
    }

    inline void avg_color(uint8_t& out_r, uint8_t& out_g, uint8_t& out_b) const {
        if (pixel_count == 0) { out_r = out_g = out_b = 0; return; }
        out_r = static_cast<uint8_t>(red_sum   / pixel_count);
        out_g = static_cast<uint8_t>(green_sum / pixel_count);
        out_b = static_cast<uint8_t>(blue_sum  / pixel_count);
    }
};

// ---------------------------------------------------------------------------
// Octree
// ---------------------------------------------------------------------------
class Octree {
public:
    static constexpr int MAX_DEPTH = 8; 

    explicit Octree()
        : leaf_count(0)
    {
        for (int i = 0; i < MAX_DEPTH; ++i)
            reducible_head[i] = nullptr;

        root = pool.allocate();
        new (root) Node();
    }

    void insert(uint8_t r, uint8_t g, uint8_t b) {
        Node* node = root;

        for (int depth = 0; depth < MAX_DEPTH; ++depth) {
            const int shift = 7 - depth;
            const int idx   = node->color_index(r, g, b, shift);

            if (!node->children[idx]) {
                Node* child = pool.allocate();
                new (child) Node();
                node->children[idx] = child;

                if (depth + 1 == MAX_DEPTH) {
                    child->is_leaf = true;
                    ++leaf_count;
                } else {

                    int lvl = depth + 1;
                    child->next_reducible = reducible_head[lvl];
                    reducible_head[lvl] = child;
                }
            }

            node = node->children[idx];
            if (node->is_leaf) break;
        }

        node->red_sum   += r;
        node->green_sum += g;
        node->blue_sum  += b;
        ++node->pixel_count;
    }

    bool reduce() {
        for (int level = MAX_DEPTH - 1; level > 0; --level) {
            while (reducible_head[level]) {
                Node* node = reducible_head[level];
                reducible_head[level] = node->next_reducible;


                if (node->is_leaf || node->is_dead) continue;

                int leaves_removed = 0;

                for (int i = 0; i < 8; ++i) {
                    Node* child = node->children[i];
                    if (!child) continue;

                    node->red_sum   += child->red_sum;
                    node->green_sum += child->green_sum;
                    node->blue_sum  += child->blue_sum;
                    node->pixel_count += child->pixel_count;

                    if (child->is_leaf) {
                        ++leaves_removed;
                    }

                    child->is_dead = true;
                    child->is_leaf = false;
                    memset(child->children, 0, sizeof(child->children));
                    child->pixel_count = 0;
                    node->children[i] = nullptr;
                }

                node->is_leaf = true;
                leaf_count -= (leaves_removed - 1);
                return true;
            }
        }
        return false;
    }

    void map_color(uint8_t r, uint8_t g, uint8_t b,
                   uint8_t& out_r, uint8_t& out_g, uint8_t& out_b) const
    {
        const Node* node = root;
        for (int depth = 0; depth < MAX_DEPTH; ++depth) {
            if (node->is_leaf) break;
            const int shift = 7 - depth;
            const int idx   = node->color_index(r, g, b, shift);
            const Node* child = node->children[idx];
            if (!child) break;
            node = child;
        }
        node->avg_color(out_r, out_g, out_b);
    }

    int leaf_count;

private:
    Node*  root;
    Node*  reducible_head[MAX_DEPTH]; 
    PoolAllocator<Node> pool;
};


extern "C" {

// Algorithm 1: Baseline — reduce inline during insertion.
void octree_quantize_baseline(uint8_t* pixels, int num_pixels, int target_colors) {
    Octree tree;

    for (int i = 0; i < num_pixels; ++i) {
        tree.insert(pixels[i*3], pixels[i*3+1], pixels[i*3+2]);
        while (tree.leaf_count > target_colors)
            if (!tree.reduce()) break;
    }

    while (tree.leaf_count > target_colors)
        if (!tree.reduce()) break;

    for (int i = 0; i < num_pixels; ++i) {
        uint8_t r_out, g_out, b_out;
        tree.map_color(pixels[i*3], pixels[i*3+1], pixels[i*3+2], r_out, g_out, b_out);
        
        pixels[i*3]   = r_out;
        pixels[i*3+1] = g_out;
        pixels[i*3+2] = b_out;
    }
}

// Algorithm 2: Two-pass — build the full tree first, then reduce to target, then remap.
void octree_quantize_two_pass(uint8_t* pixels, int num_pixels, int target_colors) {
    Octree tree;

    for (int i = 0; i < num_pixels; ++i)
        tree.insert(pixels[i*3], pixels[i*3+1], pixels[i*3+2]);

    while (tree.leaf_count > target_colors)
        if (!tree.reduce()) break;
    
    for (int i = 0; i < num_pixels; ++i) {
        uint8_t r_out, g_out, b_out;
        tree.map_color(pixels[i*3], pixels[i*3+1], pixels[i*3+2], r_out, g_out, b_out);
        
        pixels[i*3]   = r_out;
        pixels[i*3+1] = g_out;
        pixels[i*3+2] = b_out;
    }
}

} 