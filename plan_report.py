class PlanReport:
    def __init__(self, data):
        if isinstance(data, list) and len(data) == 1:
            data = data[0]
        if not isinstance(data, dict) or not isinstance(data.get("Plan"), dict):
            raise ValueError("Expected PostgreSQL EXPLAIN JSON containing a Plan object.")
        self.data = data
        self._validate(data["Plan"])

    def _validate(self, node):
        if not isinstance(node, dict) or not isinstance(node.get("Node Type"), str):
            raise ValueError("Each plan step must have a Node Type.")
        if not isinstance(node.get("Plans", []), list):
            raise ValueError("Plans must be a list of child steps.")
        for child in node.get("Plans", []):
            self._validate(child)

    def steps(self, node=None, depth=0):
        node = self.data["Plan"] if node is None else node
        yield depth, node
        for child in node.get("Plans", []):
            yield from self.steps(child, depth + 1)

    def to_text(self):
        lines = ["Query plan"]
        if "Execution Time" in self.data:
            lines.append(f"Execution time: {self.data['Execution Time']} ms")
        else:
            lines.append("Estimates only. Use --analyze to measure this query.")
        for depth, node in self.steps():
            label = node["Node Type"]
            if node.get("Relation Name"):
                label += f" on {node['Relation Name']}"
            lines.append(f"{'  ' * depth}- {label}")
            detail = f"Estimated rows: {node.get('Plan Rows', 'unknown')}"
            if "Actual Rows" in node:
                detail += f"; actual rows per loop: {node['Actual Rows']}; loops: {node.get('Actual Loops', 1)}"
            lines.append(f"{'  ' * (depth + 1)}{detail}")
            if node.get("Index Name"):
                lines.append(f"{'  ' * (depth + 1)}Index: {node['Index Name']}")
            if node.get("Rows Removed by Filter"):
                lines.append(f"{'  ' * (depth + 1)}Rows removed by filter per loop: {node['Rows Removed by Filter']}")
            if node["Node Type"] == "Seq Scan":
                lines.append(f"{'  ' * (depth + 1)}Reads the table sequentially. This can be normal for small tables or queries returning many rows.")
        return "\n".join(lines)
