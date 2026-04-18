from core.node import Node


class Octree:
    def __init__(self, max_depth=8):
        self.max_depth = max_depth
        self.root = Node(0)
        self.leaf_count = 0

        self.reducible_nodes = [[] for _ in range(self.max_depth)]

    def insert(self, r, g, b):
        node = self.root
        node.pixel_count += 1  

        for depth in range(self.max_depth):
            index = node.get_color_index(r, g, b)

            if node.children[index] is None:
                child = Node(depth + 1)
                node.children[index] = child

                if depth + 1 == self.max_depth:
                    child.is_leaf = True
                    self.leaf_count += 1
                else:
                    self.reducible_nodes[depth + 1].append(child)

            node = node.children[index]

            if node.is_leaf:
                break

        # Accumulate color at the leaf
        node.red_sum   += r
        node.green_sum += g
        node.blue_sum  += b
        node.pixel_count += 1

    def reduce_tree(self):
        for level in range(self.max_depth - 1, 0, -1):
            if self.reducible_nodes[level]:
                node = self.reducible_nodes[level].pop()

                leaf_children = 0
                for i in range(8):
                    child = node.children[i]
                    if child is not None and child.is_leaf:
                        node.red_sum   += child.red_sum
                        node.green_sum += child.green_sum
                        node.blue_sum  += child.blue_sum
                        node.pixel_count += child.pixel_count
                        node.children[i] = None
                        leaf_children += 1

                node.is_leaf = True
                self.leaf_count -= (leaf_children - 1)
                return

    def get_mapped_color(self, r, g, b):
        node = self.root
        for _ in range(self.max_depth):
            if node.is_leaf:
                break
            index = node.get_color_index(r, g, b)
            child = node.children[index]
            if child is None:
                break
            node = child

        return node.avg_color

    def get_palette(self):
        palette = []
        self._collect_leaves(self.root, palette)
        return palette

    def _collect_leaves(self, node, palette):
        if node.is_leaf:
            palette.append(node.avg_color)
            return
        for child in node.children:
            if child is not None:
                self._collect_leaves(child, palette)