import FileHandler as FH

import sounddevice as SD
import time

''' the sound data is stored as 44100hz samples. Use this samplerate to play '''
class TTSEngine:

    SHORT_LETTERS = ['b', 'c', 'd', 'g', 'h', 'k', 'p', 't']
    LONG_LETTERS = ['a', 'e', 'f', 'i', 'l', 'm', 'n', 'o', 'r', 's', 'u', 'w', 'ä', 'ö', 'ü', 'sch', 'ch']
    UNUSED_LETTERS = ['j', 'q', 'v', 'y', 'z']
    NOT_RECORDED_LETTERS = ['x']

    RECORDED_BIGRAMS = ['ba', 'be', 'bi', 'bl', 'bo', 'br', 'bu', 'bä', 'bö', 'bü', 'ga', 'ha', 'ka']

    def __init__(self, fadezone=20):
        self.handler = FH.FileHandler()
        self.fadezone = fadezone
        self.bigrams = []
        ''' combines the short and the long letters to bigrams '''
        for i in range(len(self.SHORT_LETTERS)):
            for a in range(len(self.LONG_LETTERS) - 2):
                self.bigrams.append(self.SHORT_LETTERS[i] + self.LONG_LETTERS[a])

    def run(self, phrase):
        ''' RUN
        This is the main function of the class.
        It handles the process from the input phrase to the spoken output.

        phrase: this is a string to speek - str
        '''
        phrase = phrase.lower()
        phrase = self.collectSlices(phrase)

        # these arrays can be adjusted to change the performance on specific text
        # each array slot represents the volume and the spoken length of the corresponding letter in the input text
        self.letterslices = phrase
        count = len(phrase)
        self.volume = [1.0] * count
        self.lenght = [8000] * count
        phrase = self.injectSoundData(phrase)
        phrase = self.cutSound(phrase)
        phrase = self.adjustVolume(phrase)
        phrase = self.smoothSound(phrase)
        self.play(phrase)


    def collectSlices(self, phrase):
        ''' COLLECTSLICES
        Here the phrase is sepatated into bigrams and letters.

        phrase: all lowercase input phrase - str

        return: list of letters and bigrams - str[]
        '''
        output = []
        found_bigrams = []
        # gets all bigrams in the phrase and saves them in the found_bigrams list
        for i in range(len(self.bigrams)):
            found_bigrams.append(self.findGroups(phrase, self.bigrams[i]))
        # additionally the sch and the ch need to be found and saved in lists
        sch = self.findGroups(phrase, 'sch')
        ch = self.findGroups(phrase, 'ch')
        # because the ch is also in the sch all the ch with a s in front of them need to be deletet from the list
        selected_ch = ch.copy()
        for i in range(len(sch)):
            for a in range(len(ch)):
                if ch[len(ch) - a -1] - 1 == sch[len(sch) - i - 1]:
                    selected_ch.pop(len(ch) - a - 1)
        # now all the other letters in the phrase are collected.
        i = 0
        while i < len(phrase):
            # if the letter is already in a sch or a ch it can be overjumped
            if i in sch:
                output.append('sch')
                i += 3
            elif i in selected_ch:
                output.append('ch')
                i += 2
            # oherwise it checks if there is an existing bigram
            else:
                no_bigram = True
                for a in range(len(found_bigrams)):
                    if i not in found_bigrams[a]:
                        continue
                    # if it is a bigram the corresponding bigram needs to be added to the output list
                    for q in range(len(found_bigrams[a])):
                        if i == found_bigrams[a][q]:
                            output.append(self.bigrams[a])
                            # bigrams contain two letters. So the next one can be overjumped
                            i += 2
                            break
                    no_bigram = False
                    break
                # if it isnt a sch, a ch or a bigram, the letter will be written to the array
                if no_bigram:
                    output.append(phrase[i])
                    i += 1
        return output

    def findGroups(self, phrase, group):
        ''' FINDGROUPS
        This funcion searches the phrase for given groups and returns their position in the phrase

        phrase: given phrase from the input - str
        group: group to search in the phrase - str

        return: listindex of the first letter from the found groups
        '''
        groupIndexes = []
        index = 0
        while phrase.find(group, index) != -1:
            groupIndexes.append(phrase.find(group, index))
            index = phrase.find(group, index) + len(group)
        return groupIndexes

    def injectSoundData(self, slices):
        '''INJECTSOUNDDATA
        The phrase now separated into letters and bigrams can be filled with the
        soundfiles of the corresponding letters and bigrams.

        slices: contains the letters and bigrams as a list - str[]

        return: 2 dim list of letters and bigrams as soundfile - float[][]
        '''
        soundslices = []
        for i in slices:
            soundslices.append(self.handler.read(i))
        return soundslices

    def cutSound(self, soundslices):
        ''' CUTSOUND
        All injected sounds do have a different lenght. They need to be shortend
        in this funcion.

        soundslices: the list containing all the soundfiles - float[][]

        returns: the 2 dim list of resized sounds so that all sounds do have the same lenght - float[][]
        '''
        resizedSoundSlices = []
        for i in range(len(soundslices)):
            resizedSoundSlices.append([])
            for a in range(self.lenght[i]):
                resizedSoundSlices[i].append(soundslices[i][a])
        return resizedSoundSlices

    def adjustVolume(self, cuttedsoundslices):
        ''' ADJUSTVOLUME
        if its a desire to change the volume it can be done with the global volume variable.
        Here the whole list is being multiplied with this variable to change the amplitude.

        cuttedsoundslices: the 2 dim list of soundfiles - float[][]

        returns: the 2 dim list of soundfiles with the multiplied amplitude - float[][]
        '''
        for i in range(len(cuttedsoundslices)):
            for a in range(len(cuttedsoundslices[i])):
                cuttedsoundslices[i][a] *= self.volume[i]
        return cuttedsoundslices

    def smoothSound(self, cuttedsoundslices):
        ''' SMOOTHSOUND
        The 2 dim array has no smooth transitions between the soundfiles. This affects the result with a constant clicking
        when changing the letters. To smooth this, the soundfiles can be faded into each other. There are different ways to
        fade: The two quadratic and the linear one. Here the linear one is used.

        cuttedsoundslices: the 2 dim array with the soundfiles and adjusted volume - float[][]

        returns: the final sound file as a 1 dim list - float[]
        '''

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
            '''NONFADEZONE
            The nonFadeZone is the part in a soundslice which is not affected from the crossfade.
            This depends on the faderange and on the size of the soundfile.

            slice: the soundfile to fade in / out
            prefaderange: the faderange to fade in the soundfile - int
            postfaderange: the faderange to fade out the soundfile - int

            returns: the zone of the slice which is not affected by the fade in or out - float[]
            '''
            zone = []
            for i in range(prefaderange, len(slice) - postfaderange):
                zone.append(slice[i])
            return zone

        def fadeZones(preslice, postslice, faderange):
            ''' FADEZONES
            
            preslice: the soundfile for the fadeout - float[]
            postslice: the soundfile for the fadein - float[]
            faderange: the global faderange - int

            returns: the zones to fade in the pre- and the postslice - two float[]
            '''
            prezone = []
            postzone = []
            for i in range(faderange):
                prezone.append(preslice[len(preslice) - faderange + i])
                postzone.append(postslice[i])
            return prezone, postzone

        def singleFade(slice, heading, fadezone, fade=linear):
            ''' SINGLEFADE
            This fade is used at start and end of the phrase. There is no pre- or no postslice.

            slice: the soundfile to fade - float[]
            heading: defines if it is a fade in or out - int
            fadezone: the global fadezone - int
            fade: the type of fade - funcion

            returns: the faded soundfile - float[]
            '''
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
            ''' CROSSFADE
            This fade is used between two letters. It fades the pre- and the postslice together.

            preslice: the soundfile to fade out - float[]
            postslice: the soundfile to fade in - float[]
            fade: the type of fade - function

            returns: the crossfaded soundfile - float[]
            '''
            fadedSound = [0] * len(preslice)
            for t in range(len(fadedSound)):
                u = t / float(len(fadedSound))
                amp1, amp2 = fade(u)
                sv1 = preslice[t]
                sv2 = postslice[t]
                fadedSound[t] = (sv1 * amp1) + (sv2 * amp2)
            return fadedSound

        # the sequence of the phrase fade
        speech = []
        # first the first letter needs to be faded in with a single fade and saved to the speech list
        speech.append(singleFade(cuttedsoundslices[0], 0, int(len(cuttedsoundslices[0]) / (100 / self.fadezone))))
        # for all the following letters except the last one this sequence is essential
        for i in range(len(cuttedsoundslices) - 1):
            # calculate to nonfadezone and append the part of the soundfile to the speech list (starts with the nonfadezone of the first letter)
            speech.append(nonFadeZone(cuttedsoundslices[i], int(len(cuttedsoundslices[i]) / (100 / self.fadezone)), int(len(cuttedsoundslices[i + 1]) / (100 / self.fadezone))))
            # calculate the fadezones and adds the crossfade to the speech list
            prezone, postzone = fadeZones(cuttedsoundslices[i], cuttedsoundslices[i + 1], int(len(cuttedsoundslices[i + 1]) / (100 / self.fadezone)))
            speech.append(crossfade(prezone, postzone))
        # for the last letter the nonfadezone and the fade out (single fade) needs to be appended to the speech list
        speech.append(nonFadeZone(cuttedsoundslices[-1], int(len(cuttedsoundslices[-1]) / (100 / self.fadezone)), int(len(cuttedsoundslices[-1]) / (100 / self.fadezone))))
        speech.append(singleFade(cuttedsoundslices[-1], 1, int(len(cuttedsoundslices[-1]) / (100 / self.fadezone))))

        # writes the speech list to a file and reads it to aviod bracket errors in the list for the sounddevice library
        self.handler.write(speech, "sound")
        speech = self.handler.read("sound")

        return speech

    def play(self, soundarray):
        ''' PLAY
        This finally plays the sound

        soundarray: the faded sound of the phrase - float[]
        '''
        SD.play(soundarray)
        SD.wait()