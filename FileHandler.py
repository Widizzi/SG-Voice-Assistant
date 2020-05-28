import uuid
import os

class FileHandler:
    ''' A Class used to read and write arrays from .txt files. 
    
    It's used to handle permanent storage of sounddata needed by the tts-engine.
    Additionally to the reading function, files can be written to save new data for
    the tts-engine or adjustet to change the volume
    '''

    def __init__(self):
        ''' sets the path to the file storage '''
        self.dirmane = os.path.dirname(__file__)
        self.path = os.path.join(self.dirmane, 'datastorage/')

    def write(self, data, name=""):
        ''' writes data in a file. Creates a new file if it doesn't exist.

        Parameters
        ----------
        data : nummeric array
            the data to write
        name : string, optional
            the name of the file without .txt extension (default = random generated)
        '''
        # if no name is given the name will be generated with a random uuid in hex format
        if name == "":
            name = "record_" + str(uuid.uuid4().hex) + ".txt"
        with open(self.path + name + ".txt","w+") as f:
            f.write(str(data))

    def read(self, name):
        ''' returns the extracted data from a file as an array

        reads the data as a string, removes spaces and array-brackets
        and casts the data to floats in a new array. Returns the new array.

        Parameters
        ----------
        name : str
            the name of the file to read (without .txt extension)

        Returns
        -------
        data : float array
            the data of the read file
        '''

        with open(self.path + name + ".txt", "r") as f:
            data =f.read()
            # deletes the brackets in the read string array
            data = data.strip("[ ]")
            # saves the values splitted by a comma followed by a space in a string array
            data = data.split(", ")
            #casts each value from string to float for further usage
            for i in range(len(data)):
                data[i] = float(data[i])
        return data


    def changeVolume(self, name, gain):
        ''' changes the overall volume of the given soundfile permanently

        Parameters
        ----------
        name : str
            name of the file to change without .txt extension
        gain : float
            Multiplicator for the volume (1.0 is no change)
        '''
        data = self.read(name)
        for i in range(len(data)):
            data[i] *= gain
        self.write(data, name)