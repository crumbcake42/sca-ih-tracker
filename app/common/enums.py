from enum import Enum


class TitleEnum(str, Enum):
    MR = "Mr."
    MS = "Ms."
    MRS = "Mrs."


class Boro(str, Enum):
    BROOKLYN = "BROOKLYN"
    MANHATTAN = "MANHATTAN"
    BRONX = "BRONX"
    QUEENS = "QUEENS"
    STATEN_ISLAND = "STATEN ISLAND"
