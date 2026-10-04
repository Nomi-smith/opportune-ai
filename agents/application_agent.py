class ApplicationPreparationAgent:
    def checklist(self, opportunity):
        items=["Open and verify the official opportunity page"]
        if opportunity.application_url: items.append('Open the application portal/link')
        if opportunity.deadline: items.append(f'Confirm deadline: {opportunity.deadline}')
        for field,label in [('required_documents','Prepare'),('test_requirements','Check test'),('education_requirements','Confirm education'),('language_requirements','Confirm language'),('nationality_restrictions','Check nationality/visa')]:
            values=getattr(opportunity,field,[]) or []
            for value in values:
                if str(value).strip() and str(value).strip().lower()!='n/a': items.append(f'{label}: {value}')
        items.append('Review tailored documents before submission')
        items.append('Submit manually through the official portal')
        return items
