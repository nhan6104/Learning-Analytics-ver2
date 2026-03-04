from loader.loadDimActor import LoadDimActor
from loader.loadDimTime import LoadDimTime
from loader.loadDimResource import LoadDimResource
from loader.loadDimCourse import LoadDimCourse
from loader.loadFactBehaviorOutcomeCorrelation import LoadFactBehaviorOutcomeCorrelation
from loader.loadFactClassEngagementDistribution import LoadFactClassEngagementDistribution
from loader.loadFactStudentCourseLifeCycle import LoadFactStudentCourseLifeCyle
from loader.loadFactStudentEngagementDaily import LoadFactStudentEngagementDaily
from loader.loadFactStudentRiskWeekly import LoadFactStudentRiskWeekly


class DataMartLoader:
    def __init__(self):
        self.loadDimActor = LoadDimActor()
        self.loadDimTime = LoadDimTime()
        self.loadDimResource = LoadDimResource()
        self.loadDimCourse = LoadDimCourse()
        self.loadFactBehaviorOutcomeCorrelation = LoadFactBehaviorOutcomeCorrelation()
        self.FactClassEngagementDistribution = LoadFactClassEngagementDistribution()
        self.loadFactStudentCourseLifeCyle = LoadFactStudentCourseLifeCyle()
        self.loadFactStudentEngagementDaily = LoadFactStudentEngagementDaily()
        self.FactStudentRiskWeekly = LoadFactStudentRiskWeekly()


    def load(self):
        dimActor = self.loadDimActor.load()
        dimTime = self.loadDimTime.load()

        