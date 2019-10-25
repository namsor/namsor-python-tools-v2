class NamSorToolException(Exception) :
    def __init__(self, arg1, arg2=None):
        super(NamSorToolException, self).__init__(arg1, arg2)
        self.arg1 = arg1
        self.arg2 = arg2
    
    def __reduce__(self):
        return (NamSorToolException, (self.arg1, self.arg2))


