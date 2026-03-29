from .loader.loadDimActor import LoadDimActor
from .loader.loadDimTime import LoadDimTime
from .loader.loadDimResource import LoadDimResource
from .loader.loadDimCourse import LoadDimCourse
from .loader.loadDimSection import LoadDimSection

# V1 Loaders (commented out - replaced by V2)
# from .loader.loadFactBehaviorOutcomeCorrelation import LoadFactBehaviorOutcomeCorrelation
# from .loader.loadFactClassEngagementDistribution import LoadFactClassEngagementDistribution
# from .loader.loadFactStudentCourseLifeCycle import LoadFactStudentCourseLifeCycle
# from .loader.loadFactStudentEngagementDaily import LoadFactStudentEngagementDaily
# from .loader.loadFactStudentRiskWeekly import LoadFactStudentRiskWeekly
# from .loader.loadFactActivityTransitions import LoadFactActivityTransitions
# from .loader.loadFactStudentTimeAffinity import LoadFactStudentTimeAffinity
# from .loader.loadFactStudentDeadlineProximity import LoadFactStudentDeadlineProximity
# from .loader.loadFactStudentEngagementDepth import LoadFactStudentEngagementDepth

# V2 Loaders
from .loader.loadFactBehaviorOutcomeCorrelation_v2 import LoadFactBehaviorOutcomeCorrelation_v2
from .loader.loadFactClassEngagementDistribution_v2 import LoadFactClassEngagementDistribution_v2
from .loader.loadFactStudentCourseLifeCycle_v2 import LoadFactStudentCourseLifeCycle_v2
from .loader.loadFactStudentEngagementDaily_v2 import LoadFactStudentEngagementDaily
from .loader.loadFactStudentRiskWeekly_v2 import LoadFactStudentRiskWeekly_v2
from .loader.loadFactActivityTransitions_v2 import LoadFactActivityTransitions_v2
from .loader.loadFactStudentTimeAffinity_v2 import LoadFactStudentTimeAffinity_v2
from .loader.loadFactStudentDeadlineProximity_v2 import LoadFactStudentDeadlineProximity_v2
from .loader.loadFactStudentEngagementDepth_v2 import LoadFactStudentEngagementDepth

from .models.dimActor import DimActor
from .models.dimTime import DimTime
from .models.dimCourse import DimCourse
from .models.dimResource import DimResource
from .models.dimSection import DimSection

# V1 Models (commented out - replaced by V2)
# from .models.factBehaviorOutcomeCorrelation import FactBehaviorOutcomeCorrelation
# from .models.factClassEngagementDistribution import FactClassEngagementDistribution
# from .models.factStudentCourseLifecycle import FactStudentCourseLifeCycle
# from .models.factStudentEngagementDaily import FactDailyStudentEngagement
# from .models.factStudentRiskWeekly import FactRiskStudentWeekly
# from .models.factActivityTransitions import FactActivityTransitions
# from .models.factStudentTimeAffinity import FactStudentTimeAffinity
# from .models.factStudentDeadlineProximity import FactStudentDeadlineProximity
# from .models.factStudentEngagementDepth import FactStudentEngagementDepth

# V2 Models (using same models as V1 for now - tables created by create_v2_tables.sql)
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
        # Ensure schema exists and is set correctly
        from utils.pgsql_utils import db
        db.create_schema("datamart")

        # Initialize Models (to create tables if not exists)
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

        # Initialize Loaders (V2)
        self.loadDimActor = LoadDimActor()
        self.loadDimTime = LoadDimTime()
        self.loadDimResource = LoadDimResource()
        self.loadDimCourse = LoadDimCourse()
        self.loadDimSection = LoadDimSection()
        
        # V2 Fact Loaders
        self.loadFactBehaviorOutcomeCorrelation = LoadFactBehaviorOutcomeCorrelation_v2()
        self.FactClassEngagementDistribution = LoadFactClassEngagementDistribution_v2()
        self.loadFactStudentCourseLifeCycle = LoadFactStudentCourseLifeCycle_v2()
        self.loadFactStudentEngagementDaily = LoadFactStudentEngagementDaily()
        self.FactStudentRiskWeekly = LoadFactStudentRiskWeekly_v2()
        self.loadFactActivityTransitions = LoadFactActivityTransitions_v2()
        self.loadFactStudentTimeAffinity = LoadFactStudentTimeAffinity_v2()
        self.loadFactStudentDeadlineProximity = LoadFactStudentDeadlineProximity_v2()
        self.loadFactStudentEngagementDepth = LoadFactStudentEngagementDepth()


    def load(self):
        
        # 1. Load Dimensions
        # print("Loading Dimension: Actor")
        # self.loadDimActor.load()
        # print("Loading Dimension: Time")
        # self.loadDimTime.load()
        # print("Loading Dimension: Course")
        # self.loadDimCourse.load()
        # print("Loading Dimension: Resource")
        # self.loadDimResource.load()
        # print("Loading Dimension: Section")
        # self.loadDimSection.load()

        # 2. Load Fact Tables V2 (Dependencies: Daily -> Weekly -> Distributions/Correlations)
        # print("Loading Fact: Daily Student Engagement")
        # self.loadFactStudentEngagementDaily.load()
        # print("Loading Fact: Student Risk Weekly")
        # self.FactStudentRiskWeekly.load()
        # print("Loading Fact: Student Course LifeCycle")
        # self.loadFactStudentCourseLifeCycle.load()
        print("Loading Fact: Class Engagement Distribution")
        self.FactClassEngagementDistribution.load()
        # print("Loading Fact: Behavior Outcome Correlation")
        # self.loadFactBehaviorOutcomeCorrelation.load()

        # # 3. Load Behavioral Analytics Facts V2
        # print("Loading Fact: Activity Transitions")
        # self.loadFactActivityTransitions.load()
        # print("Loading Fact: Student Time Affinity")
        # self.loadFactStudentTimeAffinity.load()
        print("Loading Fact: Student Deadline Proximity")
        self.loadFactStudentDeadlineProximity.load()
        # print("Loading Fact: Student Engagement Depth")
        # self.loadFactStudentEngagementDepth.load()

if __name__ == "__main__":
    loader = DataMartLoader()
    loader.load()