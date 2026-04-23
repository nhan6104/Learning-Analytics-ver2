class Deduplication:
    def __init__(self):
        pass

    def deduplicateDimActor(self, elements):
        pass

    def deduplicateDimContext(self, elements):
        pass

    def deduplicateDimInteractionType(self, elements):
        pass

    def deduplicateDimTime(self, elements):
        pass

    def deduplicateFactActivity(self, elements):
        pass

    def deduplicateFactQuestion(self, elements):
        pass

    def deduplicateFactQuiz(self, elements):
        pass

    def deduplicateFactSession(self, elements):
        pass

    def deduplicateFactStatement(self, elements):
        pass

    def deduplicate(self, dict_elements):
        for key, el in dict_elements.items():
            if key == "dim_interaction_type":
                dimInteractionType = self.deduplicateDimInteractionType(el)
            elif key == "dim_time":
                dimTimeDeduplicated = self.deduplicateDimTime(el)
            elif key == "dim_actor":
                dimActorDeduplicated = self.deduplicateDimActor(el)
            elif key == "fact_activity":
                factActivityDeduplicated = self.deduplicateFactActivity(el)
            elif key == "dim_context":
                dimContextDeduplicated = self.deduplicateDimContext(el)
            elif key == "fact_statement":
                factStatementDeduplicated = self.deduplicateFactStatement(el)
            elif key == "fact_session":
                factSessionDeduplicated = self.deduplicateFactSession(el)
            elif key == "fact_quiz":
                factQuizDeduplicated = self.deduplicateFactQuiz(el)
            elif key == "fact_question":
                factQuestionDeduplicated = self.deduplicateFactQuestion(el)
 