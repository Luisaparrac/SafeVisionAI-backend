"""N-ary tree: every node has one parent and any number of ordered children.

A dictionary ``key -> node`` gives direct access to any node, so looking one up
does not walk the tree.

Complexity (n = nodes):

=================  ==========
Operation          Time
=================  ==========
add_child          O(1)
find               O(1)
postorder          O(n)
=================  ==========

Space: O(n).

``postorder`` is recursive, so its stack grows with the height of the tree. The
tree of the installations has 4 levels (root, location, camera and zone), far
from the recursion limit of the interpreter.
"""

from collections.abc import Hashable


class TreeNode[K: Hashable, V]:
    __slots__ = ("key", "value", "parent", "children")

    def __init__(self, key: K, value: V, parent: "TreeNode[K, V] | None" = None) -> None:
        self.key = key
        self.value = value
        self.parent = parent
        self.children: list[TreeNode[K, V]] = []


class NaryTree[K: Hashable, V]:
    __slots__ = ("_root", "_index")

    def __init__(self, root_key: K, root_value: V) -> None:
        self._root = TreeNode(root_key, root_value)
        self._index: dict[K, TreeNode[K, V]] = {root_key: self._root}

    def add_child(self, parent_key: K, key: K, value: V) -> None:
        """Appends a node as the last child of ``parent_key``. O(1)."""
        parent = self.find(parent_key)
        if parent is None:
            raise ValueError(f"unknown parent: {parent_key!r}")
        if key in self._index:
            raise ValueError(f"duplicate key: {key!r}")
        node = TreeNode(key, value, parent)
        parent.children.append(node)
        self._index[key] = node

    def find(self, key: K) -> TreeNode[K, V] | None:
        """The node with that key, or None. O(1)."""
        return self._index.get(key)

    def postorder(self) -> list[TreeNode[K, V]]:
        """Every node after all of its children, the root last. O(n)."""
        nodes: list[TreeNode[K, V]] = []
        _visit_postorder(self._root, nodes)
        return nodes


def _visit_postorder[K: Hashable, V](node: TreeNode[K, V], nodes: list[TreeNode[K, V]]) -> None:
    for child in node.children:
        _visit_postorder(child, nodes)
    nodes.append(node)
