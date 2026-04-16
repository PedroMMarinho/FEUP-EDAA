from core.node import Node

class Octree:
    def __init__(self, max_depth=8):
        self.root = Node(0)
        self.max_depth = max_depth
        self.leaf_count = 0
        
        # Tracks nodes by depth for efficient reduction
        self.reducible_nodes = [[] for _ in range(self.max_depth)]
        
    def insert(self, r, g, b):
        current_node = self.root
        
        for _ in range(self.max_depth):
            if current_node.is_leaf:
                break
                
            index = current_node.get_color_index(r, g, b)
            
            if current_node.children[index] is None:
                new_node = Node(current_node.level + 1)
                current_node.children[index] = new_node
                
                self.reducible_nodes[current_node.level].append(new_node)
            
            current_node = current_node.children[index]
        
        if not current_node.is_leaf:
            current_node.is_leaf = True
            self.leaf_count += 1
            
        current_node.red_sum += r
        current_node.green_sum += g
        current_node.blue_sum += b
        current_node.pixel_count += 1

    def reduce_tree(self):
        """Finds the deepest parent node and merges all its children into it."""
        for level in range(self.max_depth - 1, -1, -1):
            
            if len(self.reducible_nodes[level]) > 0:
                node = self.reducible_nodes[level].pop()
                
                children_removed = 0
                for i in range(8):
                    child = node.children[i]
                    if child is not None:
                        node.red_sum += child.red_sum
                        node.green_sum += child.green_sum
                        node.blue_sum += child.blue_sum
                        node.pixel_count += child.pixel_count
                        
                        node.children[i] = None
                        children_removed += 1
                
                node.is_leaf = True
                
                self.leaf_count -= (children_removed - 1)
                return