import json


def process_knowledge_base(input_path, output_path):

    # Load the corrected knowledge base
    with open(input_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    for doc in data:

        # Only process customer call documents
        if doc.get("category") != "Customer_Calls_Dataset":
            continue

        raw_content = doc.get("content", "")

        # Case 1: Content is still raw text
        
        if isinstance(raw_content, str):

            dialogue_array = []

            lines = raw_content.strip().splitlines()

            for line in lines:

                line = line.strip()

                if not line:
                    continue

                if line.startswith("Agent:"):

                    dialogue_array.append({
                        "speaker": "Agent",
                        "text": line.replace("Agent:", "", 1).strip()
                    })

                elif line.startswith("Customer:"):

                    dialogue_array.append({
                        "speaker": "Customer",
                        "text": line.replace("Customer:", "", 1).strip()
                    })

                else:

                    dialogue_array.append({
                        "speaker": "Unknown",
                        "text": line
                    })

            # Replace raw text with structured dialogue
            doc["content"] = dialogue_array

        # Case 2: Content is already structured

        elif isinstance(raw_content, list):

            # Leave it as it is
            doc["content"] = raw_content

    # Save processed data
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"Data processed successfully: {output_path}")


# Run
process_knowledge_base(
    "corrected_knowledge_base.json",
    "final_knowledge_base.json"
)