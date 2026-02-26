import re


def parse_md(filename):
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    sections = re.split(r"\n### (.+?)\n", content)

    objects = {}

    for i in range(1, len(sections), 2):
        name = sections[i].strip()
        body = sections[i + 1]

        if not name.endswith(" Object"):
            continue

        table_pattern = re.compile(
            r"\|\s*Field (Name|Pattern)\s*\|\s*Type\s*\|\s*Description\s*\|\n[\|\-\:\s]+\n((?:\|.*?\n)+)",
            re.DOTALL,
        )
        match = table_pattern.search(body)
        if match:
            table_body = match.group(2)
            fields = []
            for line in table_body.strip().split("\n"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 4:
                    field_name_html = parts[1]
                    field_name = re.sub(
                        r'<a name=".*?"></a>', "", field_name_html
                    ).strip()
                    field_type = parts[2]

                    fields.append(
                        {
                            "name": field_name,
                            "type": field_type,
                        }
                    )
            if name in objects:
                objects[name].extend(fields)
            else:
                objects[name] = fields

    for obj, fields in objects.items():
        print(f"class {obj.replace(' Object', '')}:")
        for f in fields:
            print(f"  {f['name']}: {f['type']}")
        print()


parse_md("3.2.0.md")
