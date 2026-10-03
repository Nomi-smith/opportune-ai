class ApplicationPreparationAgent:
    def checklist(self, opportunity):
        items = ["Review the official opportunity page"]

        if opportunity.application_url:
            items.append("Open the application link")

        if opportunity.deadline:
            items.append(f"Confirm deadline: {opportunity.deadline}")

        if opportunity.requirements:
            items.extend(
                f"Prepare: {item}"
                for item in opportunity.requirements
            )

        items.append("Review generated documents before submission")
        items.append("Submit manually")

        return items
