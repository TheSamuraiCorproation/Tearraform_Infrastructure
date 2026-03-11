#!/usr/bin/env python3
# generate_logstash_pipeline.py
# Reads an XML rules file (Wazuh-like rules) and writes a Logstash filter.conf
# Usable in ansible to generate /tmp/01-rules.conf or similar.

import sys
import xml.etree.ElementTree as ET
import html
import re
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: generate_logstash_pipeline.py <rules.xml>", file=sys.stderr)
    sys.exit(2)

rules_xml = Path(sys.argv[1])
if not rules_xml.exists():
    print(f"Rules file not found: {rules_xml}", file=sys.stderr)
    sys.exit(2)

tree = ET.parse(rules_xml)
root = tree.getroot()

filter_blocks = []

def escape_for_logstash_regex(s, is_regex=False):
    # if it's a plain 'match' string, escape special regex chars
    # if is_regex=True, try to use the string as-is but escape literal forward slashes
    if is_regex:
        return s.replace('/', r'\/')
    else:
        # escape and then replace whitespace sequences with \s+ for basic flexibility
        esc = re.escape(s)
        esc = re.sub(r'\\\s+', r'\\s+', esc)
        return esc

for rule in root.findall(".//rule"):
    rid = rule.get('id', 'unknown')
    desc = (rule.findtext('description') or "").strip()
    match = rule.findtext('match')
    regex = rule.findtext('regex')

    if not (match or regex):
        continue

    if match:
        pattern = escape_for_logstash_regex(match.strip(), is_regex=False)
    else:
        pattern = escape_for_logstash_regex(regex.strip(), is_regex=True)

    # We'll test both common fields: message, process.command_line, and any top-level fields
    conds = []
    # message
    conds.append(f'[message] =~ /{pattern}/i')
    # common suricata fields
    conds.append(f'[process][command_line] =~ /{pattern}/i')
    conds.append(f'[http][request][body] =~ /{pattern}/i')
    conds.append(f'[auditd][exe] =~ /{pattern}/i')
    conds.append(f'[data] =~ /{pattern}/i')

    cond_expr = " or ".join(conds)

    # create a filter block adding a tag and a descriptive field
    safe_desc = desc.replace('"', "'")
    block = f"""
# rule {rid}: {safe_desc}
if ({cond_expr}) {{
  mutate {{
    add_tag => ["rule-{rid}"]
    add_field => {{ "rule_id" => "{rid}" "rule_description" => "{safe_desc}" }}
  }}
}}
"""
    filter_blocks.append(block)

# Write combined filter
out = []
out.append("###############################################")
out.append("# GENERATED filter file from elk_rules.xml")
out.append("###############################################")
out.append("")
out.append("filter {")
out.extend(filter_blocks)
out.append("}")  # end filter

sys.stdout.write("\n".join(out))
