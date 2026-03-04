class transformDimActor:

    def __init__(self):
        pass

    def transform(self, statement, kwargs = {}):
        actor_id = None
        if statement.actor.account:
            actor_id = statement.actor.account.name
        
        if not actor_id:
            return
            
        actor_name = statement.actor.name
        
        return {
            "actor_id": actor_id,
            "actor_name": actor_name,
        }