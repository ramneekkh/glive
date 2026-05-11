import json
import re

with open("faq_ocr.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Regex to find Q and A
# Looks for Q<number>: <question> followed by A: <answer>
# Stops when it finds the next Q<number>: or end of file
pattern = re.compile(r"Q\d+: (.*?)\n\s*A: (.*?)(?=\n\s*Q\d+:|\Z)", re.DOTALL)
matches = pattern.findall(text)

faq_data = {}
for match in matches:
    question, answer = match
    # Clean up whitespace and newlines
    question = question.strip().replace("\n", "")
    answer = answer.strip()
    faq_data[question] = answer

# Write to faq.js
with open("faq.js", "w", encoding="utf-8") as f:
    f.write("const FAQ_DATA = ")
    f.write(json.dumps(faq_data, ensure_ascii=False, indent=4))
    f.write(";\n\n")
    f.write("""function retrieve_faq_answer(query) {
    console.log("Retrieving FAQ for:", query);
    // Simple includes match
    for (const key in FAQ_DATA) {
        if (query.includes(key) || key.includes(query)) {
            return FAQ_DATA[key];
        }
    }
    return null;
}
""")

print(f"Successfully parsed {len(faq_data)} questions and updated faq.js")
