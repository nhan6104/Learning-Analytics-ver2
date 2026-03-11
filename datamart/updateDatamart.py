from .models.dimActor import DimActor
from .models.dimTime import DimTime
# from .models.dimResource import DimResource
from .models.dimCourse import DimCourse
from .models.factBehaviorOutcomeCorrelation import FactBehaviorOutcomeCorrelation
from .models.factClassEngagementDistribution import FactClassEngagementDistribution
from .models.factStudentCourseLifecycle import FactStudentCourseLifeCyle
from .models.factStudentEngagementDaily import FactDailyStudentEngagement
from .models.factStudentRiskWeekly import FactRiskStudentWeekly

class DataMarter:
    def __init__(self):
        self.DimActor = DimActor()
        self.DimTime = DimTime()
        # self.DimResource = DimResource()
        self.DimCourse = DimCourse()
        self.FactBehaviorOutcomeCorrelation = FactBehaviorOutcomeCorrelation()
        self.FactClassEngagementDistribution = FactClassEngagementDistribution()
        self.FactStudentCourseLifeCyle = FactStudentCourseLifeCyle()
        self.FactStudentEngagementDaily = FactDailyStudentEngagement()
        self.FactStudentRiskWeekly = FactRiskStudentWeekly()


    def update(self, query):
        self.DimActor.update_datamart()
        
    


        