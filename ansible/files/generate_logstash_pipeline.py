#!/usr/bin/env python3

import sys
import xml.etree.ElementTree as ET

if len(sys.argv) != 2:
    print("Usage: generate_logstash_pipeline.py <rules.xml>", file=sys.stderr)
    sys.exit(1)

xml_file = sys.argv[1]

try:
    tree = ET.parse(xml_file)
    root = tree.getroot()
except Exception as e:
    print(f"XML parsing error: {e}", file=sys.stderr)
    sys.exit(2)

rules = []

for rule in root.findall(".//rule"):

    description = rule.findtext("description") or "custom_rule"

    match = rule.findtext("match")
    regex = rule.findtext("regex")

    pattern = match if match else regex

    if pattern:
        rules.append((pattern.strip(), description.strip()))

print("""
input {
  beats {
    port => 5044
  }
}

filter {
""")

for pattern, description in rules:
    safe_tag = description.lower().replace(" ", "_")

    print(f"""
  if [message] =~ /{pattern}/ {{
    mutate {{
      add_tag => ["{safe_tag}"]
    }}
  }}
""")

print("""
}

output {

  stdout { codec => rubydebug }

}
""")
