from app.models.user import User
from app.models.student import Student, Class, Major
from app.models.training import TrainingProject, TrainingRecord, Score
from app.models.ability import MajorAbility, SubAbility, AbilityProfile
from app.models.lab import Lab, EnvironmentCheck
from app.models.report import DiagnosticReport

__all__ = [
    "User",
    "Student",
    "Class",
    "Major",
    "TrainingProject",
    "TrainingRecord",
    "Score",
    "MajorAbility",
    "SubAbility",
    "AbilityProfile",
    "Lab",
    "EnvironmentCheck",
    "DiagnosticReport",
]
