import FileHandler as FH

import sounddevice as SD
import time

class TTSEngine:

    def __init__(self, fadezone=20):
        self.handler = FH.FileHandler()
        self.fadezone = fadezone

    def run(self, phrase):
        phrase = phrase.lower()
        phrase = self.collectSlices(phrase)

        # these arrays can be adjusted to change the performance on specific text
        # each array slot represents the volume and the spoken length of the corresponding letter in the input text
        count = len(phrase)
        self.volume = [1.0] * count
        self.lenght = [8000] * count

        phrase = self.injectSoundData(phrase)
        phrase = self.cutSound(phrase)
        phrase = self.adjustVolume(phrase)
        phrase = self.smoothSound(phrase)
        self.play(phrase)


    def collectSlices(self, phrase):
        output = []
        sch = self.findGroups(phrase, 'sch')
        ch = self.findGroups(phrase, 'ch')
        selected_ch = ch.copy()
        for i in range(len(sch)):
            for a in range(len(ch)):
                if ch[len(ch) - a -1] - 1 == sch[len(sch) - i - 1]:
                    selected_ch.pop(len(ch) - a - 1)
        i = 0
        while i < len(phrase):
            if i in sch:
                output.append('sch')
                i += 3
            elif i in selected_ch:
                output.append('ch')
                i += 2
            else:
                output.append(phrase[i])
                i += 1
        return output

    def findGroups(self, phrase, group):
        groupIndexes = []
        index = 0
        while phrase.find(group, index) != -1:
            groupIndexes.append(phrase.find(group, index))
            index = phrase.find(group, index) + len(group)
        return groupIndexes

    def injectSoundData(self, slices):
        soundslices = []
        for i in slices:
            soundslices.append(self.handler.read(i))
        return soundslices

    def cutSound(self, soundslices):
        resizedSoundSlices = []
        for i in range(len(soundslices)):
            resizedSoundSlices.append([])
            for a in range(self.lenght[i]):
                resizedSoundSlices[i].append(soundslices[i][a])
        return resizedSoundSlices

    def adjustVolume(self, cuttedsoundslices):
        for i in range(len(cuttedsoundslices)):
            for a in range(len(cuttedsoundslices[i])):
                cuttedsoundslices[i][a] *= self.volume[i]
        return cuttedsoundslices

    def smoothSound(self, cuttedsoundslices):

        def quadratic_out(u):
            u = u * u
            return (1-u, u)

        def quadratic_in(u):
            u = 1-u
            u = u * u
            return (u, 1-u)

        def linear(u):
            return (1-u, u)

        def nonFadeZone(slice, prefaderange, postfaderange):
            zone = []
            for i in range(prefaderange, len(slice) - postfaderange):
                zone.append(slice[i])
            return zone

        def fadeZones(preslice, postslice, faderange):
            prezone = []
            postzone = []
            for i in range(faderange):
                prezone.append(preslice[len(preslice) - faderange + i])
                postzone.append(postslice[i])
            return prezone, postzone

        def singleFade(slice, heading, fadezone, fade=linear):
            fadeslice = []
            startindex = 0
            if heading == 1:
                startindex = len(slice) - fadezone
            else:
                startindex = 0
            for i in range(fadezone):
                fadeslice.append(slice[startindex + i])
            for t in range(len(fadeslice)):
                u = t / float(len(fadeslice))
                amp1, amp2 = fade(u)
                if heading == 1:
                    fadeslice[t] *= amp1
                else:
                    fadeslice[t] *= amp2
            return fadeslice

        def crossfade(preslice, postslice, fade=linear):
            fadedSound = [0] * len(preslice)
            for t in range(len(fadedSound)):
                u = t / float(len(fadedSound))
                amp1, amp2 = fade(u)
                sv1 = preslice[t]
                sv2 = postslice[t]
                fadedSound[t] = (sv1 * amp1) + (sv2 * amp2)
            return fadedSound

        speech = []
        speech.append(singleFade(cuttedsoundslices[0], 0, int(len(cuttedsoundslices[0]) / (100 / self.fadezone))))
        for i in range(len(cuttedsoundslices) - 1):
            speech.append(nonFadeZone(cuttedsoundslices[i], int(len(cuttedsoundslices[i]) / (100 / self.fadezone)), int(len(cuttedsoundslices[i + 1]) / (100 / self.fadezone))))
            prezone, postzone = fadeZones(cuttedsoundslices[i], cuttedsoundslices[i + 1], int(len(cuttedsoundslices[i + 1]) / (100 / self.fadezone)))
            speech.append(crossfade(prezone, postzone))
        speech.append(nonFadeZone(cuttedsoundslices[-1], int(len(cuttedsoundslices[-1]) / (100 / self.fadezone)), int(len(cuttedsoundslices[-1]) / (100 / self.fadezone))))
        speech.append(singleFade(cuttedsoundslices[-1], 1, int(len(cuttedsoundslices[-1]) / (100 / self.fadezone))))

        self.handler.write(speech, "sound")
        speech = self.handler.read("sound")

        return speech

    def play(self, soundarray):
        SD.play(soundarray)
        SD.wait()