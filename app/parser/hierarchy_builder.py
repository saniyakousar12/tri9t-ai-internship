# app/parser/hierarchy_builder.py
class HierarchyBuilder:
    def __init__(self):
        self.nodes = []
        self.current_parents = {}  # level -> parent_id
    
    def build_tree(self, headings: List[Dict]):
        """
        Strategy for parent-child relationships:
        1. Track current parent at each level
        2. When level increases, set parent as previous node
        3. When level decreases, pop parent stack
        """
        for heading in headings:
            node = self._create_node(heading)
            self._assign_parent(node)
            self._update_parent_stack(node)
            self.nodes.append(node)
        return self.nodes
    
    def _assign_parent(self, node):
        """Find appropriate parent based on level"""
        if node.level == 1:
            node.parent_id = None
        else:
            # Find most recent node at level-1
            parent = self._find_parent_at_level(node.level - 1)
            node.parent_id = parent.id if parent else None