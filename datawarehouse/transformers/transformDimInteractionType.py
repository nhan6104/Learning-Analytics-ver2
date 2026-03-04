class transformDimInteractionType:
    def __init__(self):
        pass

    def transform(self, statement, kwargs = {}):
        """Process and insert/update dim_interation_type using a simplified ID"""
        
        full_verb_id = statement.verb.id
        # Extract the last part of the URL (e.g., 'completed' from '.../verbs/completed')
        interaction_id = full_verb_id.strip('/').split('/')[-1]
        
        interaction_name = statement.verb.display.en if statement.verb.display else interaction_id.capitalize()
        
        # Refined categorization logic to reduce "Other"
        category = "Other"
        v_id = interaction_id.lower()
        
        if any(x in v_id for x in ['launched', 'start']): category = "navigation"
        elif any(x in v_id for x in ['experienced', 'receive', 'viewed']): category = "learning"
        elif any(x in v_id for x in ['answered', 'passed', 'failed']): category = "assessment"
        elif any(x in v_id for x in ['completed', 'uncompleted']): category = "assessment"

        
        return {
            "interaction_id": interaction_id,
            "interaction_name": interaction_name,
            "interaction_category": category,
        }