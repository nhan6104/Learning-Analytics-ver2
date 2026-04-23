from .loader.loadDimActor import LoadDimActor
from .loader.loadDimTime import LoadDimTime
from .loader.loadDimResource import LoadDimResource
from .loader.loadDimCourse import LoadDimCourse
from .loader.loadFactBehaviorOutcomeCorrelation import LoadFactBehaviorOutcomeCorrelation
from .loader.loadFactClassEngagementDistribution import LoadFactClassEngagementDistribution
from .loader.loadFactStudentCourseLifeCycle import LoadFactStudentCourseLifeCycle
from .loader.loadFactStudentEngagementDaily import LoadFactStudentEngagementDaily
from .loader.loadFactStudentRiskWeekly import LoadFactStudentRiskWeekly

from .models.dimActor import DimActor
from .models.dimTime import DimTime
from .models.dimCourse import DimCourse
from .models.dimResource import DimResource
from .models.factBehaviorOutcomeCorrelation import FactBehaviorOutcomeCorrelation
from .models.factClassEngagementDistribution import FactClassEngagementDistribution
from .models.factStudentCourseLifecycle import FactStudentCourseLifeCycle
from .models.factStudentEngagementDaily import FactDailyStudentEngagement
from .models.factStudentRiskWeekly import FactRiskStudentWeekly

class DataMartLoader:
    def __init__(self):
        # Ensure schema exists and is set correctly
        from utils.pgsql_utils import db
        db.create_schema("datamart")

        # Initialize Models (to create tables if not exists)
        self.dimActorModel = DimActor()
        self.dimTimeModel = DimTime()
        self.dimCourseModel = DimCourse()
        self.dimResourceModel = DimResource()
        self.factBehaviorOutcomeCorrelationModel = FactBehaviorOutcomeCorrelation()
        self.factClassEngagementDistributionModel = FactClassEngagementDistribution()
        self.factStudentCourseLifeCycleModel = FactStudentCourseLifeCycle()
        self.factStudentEngagementDailyModel = FactDailyStudentEngagement()
        self.factStudentRiskWeeklyModel = FactRiskStudentWeekly()

        # Initialize Loaders
        self.loadDimActor = LoadDimActor()
        self.loadDimTime = LoadDimTime()
        self.loadDimResource = LoadDimResource()
        self.loadDimCourse = LoadDimCourse()
        self.loadFactBehaviorOutcomeCorrelation = LoadFactBehaviorOutcomeCorrelation()
        self.FactClassEngagementDistribution = LoadFactClassEngagementDistribution()
        self.loadFactStudentCourseLifeCycle = LoadFactStudentCourseLifeCycle()
        self.loadFactStudentEngagementDaily = LoadFactStudentEngagementDaily()
        self.FactStudentRiskWeekly = LoadFactStudentRiskWeekly()


    def load(self):
        
        # 1. Load Dimensions
        print("Loading Dimension: Actor")
        self.loadDimActor.load()
        print("Loading Dimension: Time")
        self.loadDimTime.load()
        print("Loading Dimension: Course")
        self.loadDimCourse.load()
        print("Loading Dimension: Resource")
        self.loadDimResource.load()

        # 2. Load Fact Tables (Dependencies: Daily -> Weekly -> Distributions/Correlations)
        print("Loading Fact: Daily Student Engagement")
        self.loadFactStudentEngagementDaily.load()
        print("Loading Fact: Student Risk Weekly")
        self.FactStudentRiskWeekly.load()
        print("Loading Fact: Student Course LifeCycle")
        self.loadFactStudentCourseLifeCycle.load()
        print("Loading Fact: Class Engagement Distribution")
        self.FactClassEngagementDistribution.load()
        print("Loading Fact: Behavior Outcome Correlation")
        self.loadFactBehaviorOutcomeCorrelation.load()

if __name__ == "__main__":
    loader = DataMartLoader()
    loader.load()