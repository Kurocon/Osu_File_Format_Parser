import os
import re
import sys
import configparser
import logging
from pprint import pprint

import log_config


def find_songs(songs_directory):
    log.debug("Using song directory {}".format(songs_directory))
    songs = {}
    for folder in [d for d in os.listdir(songs_directory) if os.path.isdir(songs_directory + "/"+d)]:
        log.debug("Checking subfolder {}".format(folder))
        files = [f for f in os.listdir(songs_directory + "/" + folder) if f.endswith(".osu")]
        log.debug("Found {} difficulties in folder {}.".format(len(files), folder))
        songs[folder] = files

    return songs


sectionPattern = re.compile(r'^\[([a-zA-Z0-9]+)\]$')
keyvalPattern = re.compile(r'^([a-zA-Z0-9]+)\s*:\s*(.*)$')
osuversionPattern = re.compile(r'^[\s\ufeff\x7f]*osu file format v([0-9]+)\s*$')
blanklinePattern = re.compile(r'^[\s\ufeff\x7f]*$')

class OsuFileFormatException(Exception):
    pass


class OsuBeatmapVersionTooOldException(Exception):
    pass


class HitCircle:
    def __init__(self, x, y, time, type, hitsound, addition="0:0:0:0"):
        self.x = x
        self.y = y
        self.time = time
        self.type = type
        self.hitsound = hitsound
        self.addition = addition

    @classmethod
    def from_vals(cls, vals):
        if len(vals) == 6:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5])
        elif len(vals) == 5:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4])

    def __str__(self):
        return "Circle: {},{},{},{},{},{}".format(self.x, self.y, self.time, self.type, self.hitsound, self.addition)


class Slider:
    def __init__(self, x, y, time, type, hitsound, thing, repeat, pixellength, edgehitsound="0", edgeaddition="0:0|0:0", addition="0:0:0:0"):
        self.x = x
        self.y = y
        self.time = time
        self.type = type
        self.hitsound = hitsound
        self.thing = thing
        self.repeat = repeat
        self.pixellength = pixellength
        self.edgehitsound = edgehitsound
        self.edgeaddition = edgeaddition
        self.addition = addition

    @classmethod
    def from_vals(cls, vals):
        if len(vals) == 11:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7], vals[8], vals[9], vals[10])
        elif len(vals) == 10:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7], vals[8], vals[9])
        elif len(vals) == 9:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7], vals[8])
        elif len(vals) == 8:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7])

    def __str__(self):
        return "Slider: {},{},{},{},{},{},{},{},{},{}".format(self.x, self.y, self.time, self.type, self.hitsound, self.thing, self.repeat, self.pixellength, self.edgehitsound, self.edgeaddition, self.addition)


class Spinner:
    def __init__(self, x, y, time, type, hitsound, endtime, addition="0:0:0:0"):
        self.x = x
        self.y = y
        self.time = time
        self.type = type
        self.hitsound = hitsound
        self.endtime = endtime
        self.addition = addition

    @classmethod
    def from_vals(cls, vals):
        if len(vals) == 7:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6])
        elif len(vals) == 6:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5])

    def __str__(self):
        return "Slider: {},{},{},{},{},{},{}".format(self.x, self.y, self.time, self.type, self.hitsound, self.endtime, self.addition)


class TimingPoint:
    def __init__(self, offset, msperbeat, meter, sampletype, sampleset, volume="100", inherited="0", kiaimode="0"):
        self.offset = int(round(float(offset)))
        self.msperbeat = float(msperbeat)
        self.meter = int(meter)
        self.sampletype = int(sampletype)
        self.sampleset = int(sampleset)
        self.volume = int(volume)
        self.inherited = bool(int(inherited))
        self.kiaimode = bool(int(kiaimode))

    @classmethod
    def from_vals(cls, vals):
        if len(vals) == 8:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7])
        elif len(vals) == 7:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6])
        elif len(vals) == 6:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5])
        elif len(vals) == 5:
            return cls(vals[0], vals[1], vals[2], vals[3], vals[4])

    def __str__(self):
        return "TimingPoint: {},{},{},{},{},{},{},{}".format(self.offset, self.msperbeat, self.meter, self.sampletype, self.sampleset, self.volume, self.inherited, self.kiaimode)


class Colour:
    def __init__(self, r, g, b):
        self.r = int(r)
        self.g = int(g)
        self.b = int(b)

    def __str__(self):
        return "Colour: ({},{},{})".format(self.r, self.g, self.b)


class Difficulty:
    def __init__(self, path, data):
        self.path = path
        self.data = data

    def get_data(self):
        return self.data

    def get_path(self):
        return self.path

    def get_version(self):
        return self.data["version"]

    def get_colours(self, key=None):
        if key:
            return self.data["Colours"][key]
        else:
            return self.data["Colours"]

    def get_difficulty(self, key=None):
        if key:
            return self.data["Difficulty"][key]
        else:
            return self.data["Difficulty"]

    def get_ar(self):
        return self.data["Difficulty"]["ApproachRate"]

    def get_cs(self):
        return self.data["Difficulty"]["CircleSize"]

    def get_hp(self):
        return self.data["Difficulty"]["HPDrainRate"]

    def get_od(self):
        return self.data["Difficulty"]["OverallDifficulty"]

    def get_slider_multiplier(self):
        return self.data["Difficulty"]["SliderMultiplier"]

    def get_slider_tick_rate(self):
        return self.data["Difficulty"]["SliderTickRate"]

    def get_editor(self, key=None):
        if key:
            return self.data["Editor"][key]
        else:
            return self.data["Editor"]

    def get_events(self, key=None):
        if key:
            return self.data["Events"][key]
        else:
            return self.data["Events"]

    def get_general(self, key=None):
        if key:
            return self.data["General"][key]
        else:
            return self.data["General"]

    def get_audio_filename(self):
        return self.data["General"]["AudioFilename"]

    def get_audio_path(self):
        return "{}/{}".format(os.path.dirname(self.path), self.data["General"]["AudioFilename"])

    def get_audio_lead_in(self):
        return self.data["General"]["AudioLeadIn"]

    def get_countdown(self):
        return self.data["General"]["Countdown"]

    def get_mode(self):
        return self.data["General"]["Mode"]

    def get_artist(self):
        return self.data["Metadata"]["Artist"]

    def get_unicode_artist(self):
        return self.data["Metadata"]["ArtistUnicode"]

    def get_beatmap_id(self):
        return self.data["Metadata"]["BeatmapID"]

    def get_beatmap_set_id(self):
        return self.data["Metadata"]["BeatmapSetID"]

    def get_creator(self):
        return self.data["Metadata"]["Creator"]

    def get_source(self):
        return self.data["Metadata"]["Source"]

    def get_tags(self):
        return self.data["Metadata"]["Tags"]

    def get_title(self):
        return self.data["Metadata"]["Title"]

    def get_unicode_title(self):
        return self.data["Metadata"]["TitleUnicode"]

    def get_difficulty_string(self):
        return self.data["Metadata"]["Version"]

    def get_hitobjects(self):
        return self.data["HitObjects"]

    @classmethod
    def from_file(cls, filepath):
        return cls(filepath, parse_osu_file(filepath))


class Beatmap:
    def __init__(self, difficulties):
        self.difficulties = difficulties

    def add_difficulty(self, difficulty):
        self.difficulties.append(difficulty)


def parse_osu_file(path):
    log.debug("Reading .osu file {}".format(path))
    log.debug("Opening file {}".format(path))
    fobj = open("{}".format(path))

    valid = False
    data = {}
    sectiondata = {}
    sectionlist = []
    currentsection = ""

    for line in fobj:

        # Ignore blank lines, skip to the next iteration
        if line == "\n":
            continue

        # Ignore empty lines, skip to the next iteration
        blank = blanklinePattern.findall(line)
        if len(blank) > 0:
            continue

        if data == {} and not valid:

            version = osuversionPattern.findall(line)
            if len(version) > 0:
                valid = True

                data['version'] = int(version[0])
                log.debug("Osu file format version: {}".format(data['version']))

                if data['version'] < 4:
                    raise OsuBeatmapVersionTooOldException
                continue
            else:
                log.error("{} is not a valid .osu file.".format(path))
                log.debug("The line was: {}".format(line))
                raise OsuFileFormatException
        elif not valid:
            log.error("Something went wrong. {} is not a properly formatted .osu file.".format(path))
            log.debug("The line was: {}".format(line))
            raise OsuFileFormatException

        section = sectionPattern.findall(line)
        if len(section) > 0:
            if currentsection != "":
                data[currentsection] = sectionlist if sectionlist != [] else sectiondata

            sectiondata = {}
            sectionlist = []
            currentsection = section[0]
            continue

        # Parse key-value entries
        keyvalue = keyvalPattern.findall(line)
        if len(keyvalue) > 0:
            key, value = keyvalue[0]

            # Parse colour
            if currentsection == "Colours":
                vals = value.split(",")
                sectiondata[key] = Colour(vals[0], vals[1], vals[2])

            # Parse Difficulty values
            elif currentsection == "Difficulty":
                if key in ["ApproachRate", "CircleSize", "HPDrainRate", "OverallDifficulty", "SliderMultiplier", "SliderTickRate"]:
                    sectiondata[key] = float(value)
                else:
                    sectiondata[key] = value

            # Parse Editor values
            elif currentsection == "Editor":
                if key == "Bookmarks":
                    sectiondata[key] = value.split(",")
                elif key == "DistanceSpacing":
                    sectiondata[key] = float(value)
                elif key in ["BeatDivisor", "GridSize", "TimelineZoom"]:
                    sectiondata[key] = int(round(float(value)))
                else:
                    sectiondata[key] = value

            # Parse general values
            elif currentsection == "General":
                if key in ["AudioLeadIn", "PreviewTime", "Mode"]:
                    sectiondata[key] = int(value)
                elif key in ["Countdown", "LetterboxInBreaks", "WidescreenStoryboard"]:
                    sectiondata[key] = bool(int(value))
                elif key == "StackLeniency":
                    sectiondata[key] = float(value)
                else:
                    sectiondata[key] = value

            # Parse metadata values
            elif currentsection == "Metadata":
                if key in ["BeatmapID", "BeatmapSetID"]:
                    sectiondata[key] = int(value)
                elif key == "Tags":
                    sectiondata[key] = value.split()
                else:
                    sectiondata[key] = value

            # Parse other key-values
            else:
                sectiondata[key] = value
            continue

        if currentsection == "HitObjects":
            vals = line[:-1].split(",")
            type = int(vals[3])

            # Try identification based on type first:

            # Hit circle
            if type == 1 or type == 5:  # len(vals) == 6:
                sectionlist.append(HitCircle.from_vals(vals))
            # Slider
            elif type == 2 or type == 6:  # len(vals) == 11:
                sectionlist.append(Slider.from_vals(vals))
            # Spinner
            elif type == 12:  # len(vals) == 7:
                sectionlist.append(Spinner.from_vals(vals))

            # Try identification based on value length next

            # Hit circle
            elif len(vals) == 6 or len(vals) == 5:
                sectionlist.append(HitCircle.from_vals(vals))
            # Slider
            elif len(vals) == 11 or len(vals) == 10 or len(vals) == 9 or len(vals) == 8:
                sectionlist.append(Slider.from_vals(vals))
            # Spinner
            elif len(vals) == 7:
                sectionlist.append(Spinner.from_vals(vals))

            else:
                log.warning("Unknown HitObject: {}".format(vals))
            continue

        if currentsection == "TimingPoints":
            vals = line[:-1].split(",")

            if len(vals) == 8 or len(vals) == 7 or len(vals) == 6 or len(vals) == 5:
                sectionlist.append(TimingPoint.from_vals(vals))
            else:
                log.warning("Unknown TimingPoint: {}".format(vals))
            continue

        if currentsection == "Events":
            # We do not care about any storyboards.
            continue

        log.warning("Unknown line: {}".format(line))

    # Save the last section if applicable
    if currentsection != "" and (sectiondata != {} or sectionlist != []):
        data[currentsection] = sectionlist if sectionlist != [] else sectiondata

    log.debug("Parsing of {} completed.".format(path))
    log.debug("data: {}".format(data))
    return data


# Configure loggers
log_config.config()
# Get logger, overwrite to update log config
log = logging.getLogger(__name__)
log.info("Starting OsuParserTest")
#songs_dir = sys.path[0]+"/songs"

songs_dir = "/data/OwnCloud/Osu Songs"

log.info("Finding songs in directory")
song_dirs = find_songs(songs_dir)
log.info("Found {} songs in the songs directory".format(len(song_dirs)))

log.info("Loading songs into memory...")
songs = []
difficulty_count = 0
skipped_difficulties = 0
for s in list(song_dirs.keys()):
    log.info("Loading song {}".format(s))
    song = Beatmap([])
    for diff in song_dirs.get(s):
        log.debug("Loading difficulty {}".format(diff))
        try:
            difficulty = Difficulty.from_file("/".join([songs_dir, s, diff]))
            song.add_difficulty(difficulty)
            difficulty_count += 1
        except OsuBeatmapVersionTooOldException:
            log.warning("The beatmap {}/{} was of a too old version and was skipped.".format(s, diff))
            skipped_difficulties += 1
    songs.append(song)

log.info("Loaded {} songs and {} difficulties into memory. {} were skipped because they were too old.".format(len(songs), difficulty_count, skipped_difficulties))
