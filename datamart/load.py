from .loader.loadDimActor import LoadDimActor
from .loader.loadDimTime import LoadDimTime
from .loader.loadDimResource import LoadDimResource
from .loader.loadDimCourse import LoadDimCourse
from .loader.loadDimSection import LoadDimSection
from .loader.loadFactBehaviorOutcomeCorrelation import LoadFactBehaviorOutcomeCorrelation
from .loader.loadFactClassEngagementDistribution import LoadFactClassEngagementDistribution
from .loader.loadFactStudentCourseLifeCycle import LoadFactStudentCourseLifeCycle
from .loader.loadFactStudentEngagementDaily import LoadFactStudentEngagementDaily
from .loader.loadFactStudentRiskWeekly import LoadFactStudentRiskWeekly
from .loader.loadFactActivityTransitions import LoadFactActivityTransitions
from .loader.loadFactStudentTimeAffinity import LoadFactStudentTimeAffinity
from .loader.loadFactStudentDeadlineProximity import LoadFactStudentDeadlineProximity
from .loader.loadFactStudentEngagementDepth import LoadFactStudentEngagementDepth

from .models.dimActor import DimActor
from .models.dimTime import DimTime
from .models.dimCourse import DimCourse
from .models.dimResource import DimResource
from .models.dimSection import DimSection
from .models.factBehaviorOutcomeCorrelation import FactBehaviorOutcomeCorrelation
from .models.factClassEngagementDistribution import FactClassEngagementDistribution
from .models.factStudentCourseLifecycle import FactStudentCourseLifeCycle
from .models.factStudentEngagementDaily import FactDailyStudentEngagement
from .models.factStudentRiskWeekly import FactRiskStudentWeekly
from .models.factActivityTransitions import FactActivityTransitions
from .models.factStudentTimeAffinity import FactStudentTimeAffinity
from .models.factStudentDeadlineProximity import FactStudentDeadlineProximity
from .models.factStudentEngagementDepth import FactStudentEngagementDepth

class DataMartLoader:
    def __init__(self):
        from utils.pgsql_utils import db
        db.create_schema("datamart")

        # Initialize Models
        self.dimActorModel = DimActor()
        self.dimTimeModel = DimTime()
        self.dimCourseModel = DimCourse()
        self.dimResourceModel = DimResource()
        self.dimSectionModel = DimSection()
        self.factBehaviorOutcomeCorrelationModel = FactBehaviorOutcomeCorrelation()
        self.factClassEngagementDistributionModel = FactClassEngagementDistribution()
        self.factStudentCourseLifeCycleModel = FactStudentCourseLifeCycle()
        self.factStudentEngagementDailyModel = FactDailyStudentEngagement()
        self.factStudentRiskWeeklyModel = FactRiskStudentWeekly()
        self.factActivityTransitionsModel = FactActivityTransitions()
        self.factStudentTimeAffinityModel = FactStudentTimeAffinity()
        self.factStudentDeadlineProximityModel = FactStudentDeadlineProximity()
        self.factStudentEngagementDepthModel = FactStudentEngagementDepth()

        # Initialize Loaders
        self.loadDimActor = LoadDimActor()
        self.loadDimTime = LoadDimTime()
        self.loadDimResource = LoadDimResource()
        self.loadDimCourse = LoadDimCourse()
        self.loadDimSection = LoadDimSection()
        self.loadFactBehaviorOutcomeCorrelation = LoadFactBehaviorOutcomeCorrelation()
        self.loadFactClassEngagementDistribution = LoadFactClassEngagementDistribution()
        self.loadFactStudentCourseLifeCycle = LoadFactStudentCourseLifeCycle()
        self.loadFactStudentEngagementDaily = LoadFactStudentEngagementDaily()
        self.loadFactStudentRiskWeekly = LoadFactStudentRiskWeekly()
        self.loadFactActivityTransitions = LoadFactActivityTransitions()
        self.loadFactStudentTimeAffinity = LoadFactStudentTimeAffinity()
        self.loadFactStudentDeadlineProximity = LoadFactStudentDeadlineProximity()
        self.loadFactStudentEngagementDepth = LoadFactStudentEngagementDepth()

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
        print("Loading Dimension: Section")
        self.loadDimSection.load()

        # 2. Load Fact Tables
        print("Loading Fact: Daily Student Engagement")
        self.loadFactStudentEngagementDaily.load()
        print("Loading Fact: Student Risk Weekly")
        self.loadFactStudentRiskWeekly.load()
        print("Loading Fact: Student Course LifeCycle")
        self.loadFactStudentCourseLifeCycle.load()
        print("Loading Fact: Class Engagement Distribution")
        self.loadFactClassEngagementDistribution.load()
        print("Loading Fact: Behavior Outcome Correlation")
        self.loadFactBehaviorOutcomeCorrelation.load()
        print("Loading Fact: Activity Transitions")
        self.loadFactActivityTransitions.load()
        print("Loading Fact: Student Time Affinity")
        self.loadFactStudentTimeAffinity.load()
        print("Loading Fact: Student Deadline Proximity")
        self.loadFactStudentDeadlineProximity.load()
        print("Loading Fact: Student Engagement Depth")
        self.loadFactStudentEngagementDepth.load()

if __name__ == "__main__":
    loader = DataMartLoader()
    loader.load()
