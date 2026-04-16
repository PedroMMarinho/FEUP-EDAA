class Node:
    def __init__(self, level):
        self.level = level           # Tree depth (0 to 7)
        self.children = [None] * 8   
        self.is_leaf = False         
        
        # Color data 
        self.pixel_count = 0         
        self.red_sum = 0             
        self.green_sum = 0           
        self.blue_sum = 0            

    def get_color_index(self, r, g, b):
        shift = 7 - self.level
        
        r_bit = (r >> shift) & 1
        g_bit = (g >> shift) & 1
        b_bit = (b >> shift) & 1
        
        return (r_bit << 2) | (g_bit << 1) | b_bit