"""
transcription.py
----------------
Converts a raw braille Unicode string (Grade 2 / UEB) into printed English
and wraps the result in RTF formatting commands.

This is a clean refactoring of the transcription logic from the original
e-braille-tales.py.  All braille data and disambiguation rules are preserved
exactly; the code is wrapped in a single public function for easy reuse.

Usage:
    from braille_ocr.core.transcription import transcribe_to_rtf
    rtf_body = transcribe_to_rtf(braille_string)
"""

import re


def transcribe_to_rtf(character_string: str) -> str:
    """
    Transcribe *character_string* (raw braille Unicode, Grade 2 / UEB) to a
    printed-English string with embedded RTF formatting commands.

    Returns the RTF body text (without the outer RTF envelope — that is added
    by write_rtf()).
    """
    dot_locator = re.compile("⠨⠿")
    new_character_string = re.sub(dot_locator,"", character_string) + "⠀"
    
    #The transcriber-defined typeform indicators must be removed from the printed English transcription,
    #(This step will not be performed when generating the PEF file.)
    tdti_list = ["⠈⠼⠂", "⠈⠼⠆", "⠈⠼⠶", "⠈⠼⠠", "⠘⠼⠂", "⠘⠼⠆", "⠘⠼⠶", "⠘⠼⠠", "⠸⠼⠂", "⠸⠼⠆", "⠸⠼⠶",
    "⠸⠼⠠", "⠐⠼⠂", "⠐⠼⠆", "⠐⠼⠶", "⠐⠼⠠", "⠨⠼⠂", "⠨⠼⠆", "⠨⠼⠶" "⠨⠼⠠"]
    for tdti in tdti_list:
        new_character_string = re.sub(tdti, "", new_character_string)
    
    #I didn't include the "horizontal line mode indicator, ⠐⠒", as I don't believe that this application
    #would be used to draw diagrams anyways. Should it be considered by the current code, it would need
    #to be removed in the English printed format, as was done above for other characters.
    
    
    #The following three final-letter groupsigns map to printed English suffixes (less, ness, sion)
    #that can also form whole words. These braille groupsigns therefore cannot be used to
    #designate a whole word, in order to avoid such ambiguities as " ⠰⠎ " meaning "grade 1 's'".
    #Substitutions are thus made only if the matches are preceded by a braille character that maps
    #to a letter or to letters. Because of this ambiguity, the transcription of the final-letter
    #groupsign "ness" needs to be done before dealing with the Grade I. Handling the final-letter
    #groupsigns "less" and "sion" before dealing with Grade I shouldn't pose a problem,
    #as the first character of both these groupsigns ("⠨") isn't a letter and therefore wouldn't
    #be found in a Group I passage.
    braille_alphabet = ["⠁", "⠃", "⠉", "⠙", "⠑", "⠋", "⠛", "⠓", "⠊", "⠚", "⠅", "⠇", "⠍", "⠝",
    "⠕", "⠏", "⠟", "⠗", "⠎", "⠞", "⠥", "⠧", "⠺", "⠭", "⠽", "⠵", "a", "b", "c", "d", "e", "f",
    "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
    contraction_characters = ["⠡", "⠩", "⠹", "⠱", "⠳", "⠌", "⠣", "⠫", "⠻", "⠪", "⠜", "⠬",
    "⠲", "⠢", "⠔", "⠯", "⠿", "⠷", "⠮", "⠾"]
    ambiguous_characters = ["⠆", "⠒", "⠖", "⠶", "⠂"]
    groupsign_list = [["⠨⠎", "less"],["⠰⠎", "ness"],["⠨⠝", "sion"]]
    for groupsign in groupsign_list:
        groupsign_matches = re.finditer(groupsign[0], new_character_string)
        groupsign_match_indices = [match.start() for match in groupsign_matches]
        #The substitutions proceed in reverse order (starting from the last hit in "new_character_string"),
        #since every two braille character sequence is changed for their four-letter long printed English
        #equivalent. This would result in indexing issues if the changes were performed from the
        #beginning of the document (from the first hit in "new_character_string").
        for i in range(len(groupsign_match_indices)-1, -1, -1):
            if (groupsign_match_indices[i] > 0 and new_character_string[groupsign_match_indices[i]-1] in
            (braille_alphabet + contraction_characters + ambiguous_characters)):
                new_character_string = (new_character_string[:groupsign_match_indices[i]]
                + groupsign[1] + new_character_string[groupsign_match_indices[i]+2:])
    
    #The following section deals with grade I passage, word and symbol indicators.
    #This section, along with the numerals section below, needs to be carried out before
    #doing any other changes to the document, to avoid mixups. Whenever a grade I symbol
    #indicator ("⠰") is found before "⠔" or "⠢", it is changed for
    #"⠰⠔" (superscript indicator) or "⠰⠢" (subscript indicator), respectively,
    #as the grade I symbol would otherwise be removed from "⠔" or "⠢" when the code skips
    #over the index at which it found "⠰" (new_character_string[index_grade_I_terminator+2:]).
    #The superscript and subscript indicators will be processed towards the end of the code,
    #hence the need to keep them in "new_character_string" until then.
    grade_I_characters = {"⠁":"a", "⠃":"b", "⠉":"c", "⠙":"d", "⠑":"e",
    "⠋":"f", "⠛":"g", "⠓":"h", "⠊":"i", "⠚":"j", "⠅":"k", "⠇":"l", "⠍":"m",
    "⠝":"n", "⠕":"o", "⠏":"p", "⠟":"q", "⠗":"r", "⠎":"s", "⠞":"t", "⠥":"u",
    "⠧":"v", "⠺":"w", "⠭":"x", "⠽":"y", "⠵":"z", "⠂":",", "⠲":".", "⠦":"?",
    "⠖":"!", "⠄":"’", "⠤":"-", "⠦":'“', "⠴":'”', "⠒": ":",
    "⠆": ";", "⠶": r"\'27", "⠔":"⠰⠔", "⠢":"⠰⠢"}
    #When the grade I passage indicator "⠰⠰⠰" is encountered, grade I transcription
    #continues until the grade I terminator symbol ("⠰⠄") is met.
    mapping_table_grade_I = new_character_string.maketrans(grade_I_characters)
    grade_I_passage_matches = re.finditer("⠰⠰⠰", new_character_string)
    grade_I_passage_match_indices = [match.start() for match in grade_I_passage_matches]
    for i in range(len(grade_I_passage_match_indices)-1, -1, -1):
        #A try except statement is included in case the user forgot to include a grade I braille
        #terminator for the grade I passage, as the program result in a ValueError would be returned
        #if there were no terminators after the grade I passage indicator. If a terminator was found
        #after the grade I passage initiator ("⠰⠰⠰"), the "new_character_string" is updated by first
        #adding all the characters up to "⠰⠰⠰" (skipping over the grade I initiator). The grade I
        #transcribed passage is then added and the remainder of "new_character_string" starting three
        #characters after "index_grade_I_terminator", such that the grade I initiator "⠰⠰⠰" is
        #not included in the updated version of "new_character_string". Similarly, "+2" is added to
        #the hit index in "new_character_string[index_grade_I_terminator+2:]", in order to skip over the
        #grade I terminator "⠰⠄".
        try:
            index_grade_I_terminator = new_character_string.index("⠰⠄", grade_I_passage_match_indices[i]+3)
            passage_string = (new_character_string[grade_I_passage_match_indices[i]+3:index_grade_I_terminator]
            .translate(mapping_table_grade_I))
            new_character_string = (new_character_string[:grade_I_passage_match_indices[i]] +
            passage_string + new_character_string[index_grade_I_terminator+2:])
        except:
            #An empty braille cell (u"\u2800") must be included after the error message within
            #brackets found below, so that the code can check for wordsigns that must stand alone
            #(be preceded by a space, hyphen/dashes, formatting indicators, suitable punctuation marks).
            #The empty braille cell will act as a "stand alone" delimitor for any wordsigns after it.
            new_character_string = (new_character_string[:grade_I_passage_match_indices[i]] +
            "[Transcription note: a grade I passage indicator was located here, but no grade I terminator was found after it.]⠀" +
            new_character_string[grade_I_passage_match_indices[i]+3:])
    
    #When the grade I word indicator "⠰⠰" is encountered, grade I transcription continues
    #until one of the following are met: an empty braille cell (u"\u2800"), the grade I
    #termination symbol ("⠰⠄") or  a hyphen ("⠤" or dash symbols such as
    #dash/en dash("⠠⠤"), long dash/em dash("⠐⠠⠤"), or underscore ("⠨⠤")).
    grade_I_word_matches = re.finditer("⠰⠰", new_character_string)
    grade_I_word_match_indices = [match.start() for match in grade_I_word_matches]
    for i in range(len(grade_I_word_match_indices)-1, -1, -1):
        word_starting_index = grade_I_word_match_indices[i]+2
    
        #The indices of all possible terminators are determined using the find() method.
        #Should there be no terminator found for a given terminator category, the
        #find() function will return -1. The lengths of the terminators are included
        #(as the second element (index 1) in each list) in order to only skip over the
        #grade I terminator symbols ("⠰⠄").
        next_empty_braille_cell = [new_character_string.find(u"\u2800", word_starting_index), 0]
        next_grade_I_terminator = [new_character_string.find("⠰⠄", word_starting_index), 2]
        next_underscore = [new_character_string.find("⠨⠤", word_starting_index), 0]
        next_dash = [new_character_string.find("⠠⠤", word_starting_index), 0]
        next_long_dash = [new_character_string.find("⠐⠠⠤", word_starting_index),0]
        next_hyphen = [new_character_string.find("⠤", word_starting_index), 0]
    
        #The results from the terminator searches above are combined in the list of lists
        #"index_categories" and sorted according to their first element (index 0), such
        #that the earliest occurence of a terminator is the first element of the list of lists.
        index_categories = sorted([next_empty_braille_cell, next_grade_I_terminator,
        next_underscore, next_dash, next_long_dash, next_hyphen], key=lambda x:x[0])
    
        #The indices in the sorted list "index_categories" that are not -1 (no found hits)
        #are pooled in the list "terminator_indices" and the first and earliest index is
        #selected as the "index_next_grade_I_terminator". The length of the terminator
        #is stored in the "terminator_length" variable.
        terminator_indices = [element for element in index_categories if element[0] != -1]
        #The "index_grade_I_terminator" is initialized to None, as indexing the list
        #terminator_indices will only be possible if a terminator was found after "⠰⠰"
        index_next_grade_I_terminator = None
        if terminator_indices != []:
            index_next_grade_I_terminator = terminator_indices[0][0]
            terminator_length = terminator_indices[0][1]
    
        #If a terminator was found after the grade I word initiator ("⠰⠰"), the
        #"new_character_string" is updated by first adding all the characters up
        #to "⠰⠰" (skipping over the grade I initiator). The grade I transcribed
        #word is then added and the remainder of "new_character_string" starting
        #from the terminator index (except for the grade I terminator symbols ("⠰⠄"),
        #which are skipped over, as the "terminator_length" is then 2) is then appended,
        #hence adding "terminator_length" to the index of the terminator.
        if index_next_grade_I_terminator != None:
            word_string = (new_character_string[word_starting_index:index_next_grade_I_terminator]
            .translate(mapping_table_grade_I))
            new_character_string = (new_character_string[:grade_I_word_match_indices[i]] +
            word_string + new_character_string[index_next_grade_I_terminator+terminator_length:])
        #If there isn't a terminator after the grade I word, the remainder of the text will be
        #transcribed using grade I braille.
        elif index_next_grade_I_terminator == None:
            word_string = new_character_string[word_starting_index:].translate(mapping_table_grade_I)
            new_character_string = (new_character_string[:grade_I_word_match_indices[i]] +
            word_string)
    
    #In all these cases, the preceding character to the final-letter groupsigns should be a braille character
    #mapping to a letter. Conversely, the single letters preceded by a Grade I symbol shouldn't be preceded
    #by a letter before the Grade I symbol ("⠰"). The printed English letters were added to the "braille_alphabet"
    #list to take into account the braille characters that are already converted to printed English letters.
    grade_I_ambiguities = [[["⠑", "e"], ["⠑", "ence"]], [["⠛", "g"], ["⠰⠛", "ong"]], [["⠇", "l"],
    ["⠇", "ful"]], [["⠝", "n"], ["⠝", "tion"]], [["⠞", "t"], ["⠞", "ment"]], [["⠽", "y"], ["⠽", "ity"]]]
    grade_I_symbol_matches = re.finditer("⠰", new_character_string)
    grade_I_symbol_match_indices = [match.start() for match in grade_I_symbol_matches]
    for i in range(len(grade_I_symbol_match_indices)-1, -1, -1):
        character_after_grade_I_symbol = new_character_string[grade_I_symbol_match_indices[i]+1]
        #The "match_found" variable will be set to "True" if the character following the grade I symbol
        #corresponds to one of the following ambiguous characters: "⠑", "⠛", "⠇", "⠝", "⠞", "⠽".
        match_found = False
        for char in grade_I_ambiguities:
            #If a match was found in "grade_I_ambiguities" and that the preceding braille
            #character maps to a letter or dash (although the final-letter groupsigns should
            #only follow letters according to the National Federation of the Blind (NFB), but dashes/hyphens
            #were allowed in this code for more leniency as to where a hyphen may be placed in a word),
            #then the ambiguous character is determined to be the corresponding final
            #letter groupsign, as a letter character wouldn't precede a grade I symbol character.
            #"+2" is added to the hit index in "new_character_string[grade_I_symbol_match_indices[i] + 2:]",
            #as the index of the hit itself is the grade I symbol "⠰", and since the grade I symbol and its
            #following braille character need to be skipped when adding the remainder of the
            #"new_character_string" after the hit.
            if (char[0][0] == character_after_grade_I_symbol and
            new_character_string[grade_I_symbol_match_indices[i]-1] in
            (braille_alphabet + contraction_characters + ["⠤"])):
                new_character_string = (new_character_string[:grade_I_symbol_match_indices[i]]
                + char[1][1] + new_character_string[grade_I_symbol_match_indices[i] + 2:])
                match_found = True
            #If a match was found in "grade_I_ambiguities" and that the preceding braille
            #character does not map to a letter, then the ambiguous character is determined to be
            #the grade I letter, as the final letter groupsigns need to be preceded by a letter.
            elif (char[0][0] == character_after_grade_I_symbol and
            new_character_string[grade_I_symbol_match_indices[i]-1] not in
            (braille_alphabet + contraction_characters + ["⠤"])):
                new_character_string = (new_character_string[:grade_I_symbol_match_indices[i]]
                + char[0][1] + new_character_string[grade_I_symbol_match_indices[i] + 2:])
                match_found = True
    
        #If no match was found in "grade_I_ambiguities" for the character following the grade I symbol,
        #and there is only one character after the grade I symbol character, then that character is mapped
        #to its letter.
        if match_found == False and grade_I_symbol_match_indices[i] == len(new_character_string) -2:
            try:
                letter = grade_I_characters[character_after_grade_I_symbol]
                new_character_string = (new_character_string[:grade_I_symbol_match_indices[i]]
                + letter)
            except:
                #If the character after the grade I symbol was not recognized as a letter, then the
                #following error message will be included in the text. The character that was originally
                #following the grade I symbol will directly follow the error message, hence the "+1"
                #in "new_character_string[grade_I_symbol_match_indices[i]+1]".
                new_character_string = (new_character_string[:grade_I_symbol_match_indices[i]] +
                "[Transcription note: a grade I symbol character was found here, but the following character was not recognized as a letter, and so could not be transcribed in grade I.]⠀" +
                new_character_string[grade_I_symbol_match_indices[i]+1])
        #If no match was found in "grade_I_ambiguities" for the character following the grade I symbol,
        #and that there are at least two characters following the grade I symbol character, then
        #the character following the grade I symbol is mapped to its letter and the other characters
        #following it are added at the end.
        elif match_found == False:
            try:
                letter = grade_I_characters[character_after_grade_I_symbol]
                new_character_string = (new_character_string[:grade_I_symbol_match_indices[i]]
                + letter + new_character_string[grade_I_symbol_match_indices[i] + 2:])
            except:
                #If the character after the grade I symbol was not recognized as a letter, then the
                #following error message will be included in the text. The character that was originally
                #following the grade I symbol will directly follow the error message, hence the "+1"
                #in "new_character_string[grade_I_symbol_match_indices[i]+1]".
                new_character_string = (new_character_string[:grade_I_symbol_match_indices[i]] +
                "[Transcription note: a grade I symbol character was found here, but the following character was not recognized as a letter, and so could not be transcribed in grade I.]⠀" +
                new_character_string[grade_I_symbol_match_indices[i]+1:])
    
    #The following section deals with numerals, which are transcribed on a one-to-one basis
    #based on their a-j braille equivalents. This section, along with the grade I section
    #above, needs to be carried out before doing any other changes to the document, to avoid mixups.
    numeral_characters = {"⠁":"1", "⠃":"2", "⠉":"3", "⠙":"4", "⠑":"5",
    "⠋":"6", "⠛":"7", "⠓":"8", "⠊":"9", "⠚":"0", "⠂": ",", "⠲": ".", "⡈":"/"}
    #When the numeric indicator "⠼" is encountered, transcription of the numerals continue as long as
    #the following characters are encountered: the braille characters for letters "a" to "j",
    #commas "⠂", periods "⠲" (or decimal points or computer dots) and fraction lines "⡈".
    mapping_table_numerals = new_character_string.maketrans(numeral_characters)
    numeric_symbol_matches = re.finditer("⠼", new_character_string)
    numeric_symbol_match_indices = [match.start() for match in numeric_symbol_matches]
    list_of_numeral_characters = ["⠁", "⠃", "⠉", "⠙", "⠑", "⠋", "⠛", "⠓", "⠊", "⠚", "⠂", "⠲", "⡈"]
    #Looping through the "numeric_symbol_match_indices" list in reverse order, as some numeric symbols "⠼"
    #will be removed as the braille digits are converted to the printed numbers. This way, we avoid staggering
    #the indices.
    for i in range(len(numeric_symbol_match_indices)-1, -1, -1):
        #The "terminator_found" variable is set to its default value of "False" and will
        #be changed to "True" when a character does not match one found in the "list_of_numeral_characters".
        #The index of this character will be stored in the "index_numeral_terminator" variable and the "for j in..."
        #loop will be broken. Since the character at the "index_numeral_terminator" is relevant and needs to
        #be maintained in the updated "new_character_string", nothing is added to it when adding the
        #remainder of the string after the hit ("new_character_string[index_numeral_terminator:]"), as
        #opposed to some grade I examples above which had superfluous braille terminator characters "⠰⠄"
        #that needed to be skipped over by adding +2 to the index of the terminator.
        terminator_found = False
        #The first numeric symbol match screened is actually the last one found in the document
        #(to prevent staggering indices when removing the numeric indicator symbols "⠼"),
        #when i equals the last index in the list "numeric_symbol_match_indices".
        if i == len(numeric_symbol_match_indices)-1:
            for j in range(numeric_symbol_match_indices[i]+1, len(new_character_string)):
                if new_character_string[j] not in list_of_numeral_characters:
                    index_numeral_terminator = j
                    numeral_string = (
                    new_character_string[numeric_symbol_match_indices[i]+1:index_numeral_terminator]
                    .translate(mapping_table_numerals))
                    new_character_string = (new_character_string[:numeric_symbol_match_indices[i]] +
                    numeral_string + new_character_string[index_numeral_terminator:])
                    terminator_found = True
                    break
        else:
            for k in range(numeric_symbol_match_indices[i]+1, numeric_symbol_match_indices[i+1]):
                if new_character_string[k] not in list_of_numeral_characters:
                    index_numeral_terminator = k
                    numeral_string = (
                    new_character_string[numeric_symbol_match_indices[i]+1:index_numeral_terminator]
                    .translate(mapping_table_numerals))
                    new_character_string = (new_character_string[:numeric_symbol_match_indices[i]] +
                    numeral_string + new_character_string[index_numeral_terminator:])
                    terminator_found = True
                    break
    
        #In the event that only characters found in the list "list_of_numeral_characters" were
        #encountered in the "for j (or k) in..." loop, then all the characters from the index
        #new_character_string[numeric_symbol_match_indices[i]+1 (following the numeric symbol)
        #up to the index of the following numeric symbol will be converted to numbers. In the
        #case of the first numeric match analyzed (which is actually the last occurence of
        #the numeric symbol in the document) the transcription to numbers occurs until the
        #end of the document and "new_character_string[index_numeral_terminator:]" is not
        #added after the "numeral_string".
        if terminator_found == False and i == len(numeric_symbol_match_indices)-1:
            numeral_string = (new_character_string[numeric_symbol_match_indices[i]+1:]
            .translate(mapping_table_numerals))
            new_character_string = (new_character_string[:numeric_symbol_match_indices[i]] +
            numeral_string)
        elif terminator_found == False and i != len(numeric_symbol_match_indices)-1:
            index_numeral_terminator = numeric_symbol_match_indices[i+1]
            numeral_string = (new_character_string[numeric_symbol_match_indices[i]+1:index_numeral_terminator]
            .translate(mapping_table_numerals))
            new_character_string = (new_character_string[:numeric_symbol_match_indices[i]] +
            numeral_string + new_character_string[index_numeral_terminator:])
    
    
    #Notice that "perceiving" is being substituted before "perceive", to avoid being left with "⠛",
    #should the substitution proceed in the reverse order. The words in "shortform_words" are then
    #be sorted by decreasing length of braille characters.
    #Please consult the following reference for a list of UEB contractions:
    #https://www.brailleauthority.org/ueb/symbols_list.pdf. All of the contractions and combined braille
    #symbols must be processed before individually transcribing the remaining characters on a one to one basis
    #to their printed English equivalents.
    shortform_words = [['⠏⠻⠉⠧⠛', 'perceiving'], ['⠽⠗⠧⠎', 'yourselves'], ['⠮⠍⠧⠎', 'themselves'],
    ['⠗⠚⠉⠛', 'rejoicing'], ['⠗⠉⠧⠛', 'receiving'], ['⠏⠻⠉⠧', 'perceive'], ['⠳⠗⠧⠎', 'ourselves'],
    ['⠙⠉⠇⠛', 'declaring'], ['⠙⠉⠧⠛', 'deceiving'], ['⠒⠉⠧⠛', 'conceiving'], ['⠁⠋⠺⠎', 'afterwards'],
    ['⠽⠗⠋', 'yourself'], ['⠞⠛⠗', 'together'], ['⠹⠽⠋', 'thyself'], ['⠗⠚⠉', 'rejoice'], ['⠗⠉⠧', 'receive'],
    ['⠏⠻⠓', 'perhaps'], ['⠐⠕⠋', 'oneself'], ['⠝⠑⠊', 'neither'], ['⠝⠑⠉', 'necessary'], ['⠍⠽⠋', 'myself'],
    ['⠊⠍⠍', 'immediate'], ['⠓⠍⠋', 'himself'], ['⠓⠻⠋', 'herself'], ['⠛⠗⠞', 'great'], ['⠙⠉⠇', 'declare'],
    ['⠙⠉⠧', 'deceive'], ['⠒⠉⠧', 'conceive'], ['⠃⠗⠇', 'braille'], ['⠁⠇⠺', 'always'], ['⠁⠇⠞', 'altogether'],
    ['⠁⠇⠹', 'although'], ['⠁⠇⠗', 'already'], ['⠁⠇⠍', 'almost'], ['⠁⠛⠌', 'against'], ['⠁⠋⠝', 'afternoon'],
    ['⠁⠋⠺', 'afterward'], ['⠁⠉⠗', 'across'], ['⠁⠃⠧', 'above'], ['⠽⠗', 'your'], ['⠺⠙', 'would'], ['⠞⠝', 'tonight'],
    ['⠞⠍', 'tomorrow'], ['⠞⠙', 'today'], ['⠎⠡', 'such'], ['⠩⠙', 'should'], ['⠎⠙', 'said'], ['⠟⠅', 'quick'],
    ['⠏⠙', 'paid'], ['⠍⠌', 'must'], ['⠍⠡', 'much'], ['⠇⠇', 'little'], ['⠇⠗', 'letter'], ['⠭⠋', 'itself'],
    ['⠭⠎', 'its'], ['⠓⠍', 'him'], ['⠛⠙', 'good'], ['⠋⠗', 'friend'], ['⠋⠌', 'first'], ['⠑⠊', 'either'],
    ['⠉⠙', 'could'], ['⠡⠝', 'children'], ['⠃⠇', 'blind'], ['⠁⠇', 'also'], ['⠁⠛', 'again'],
    ['⠁⠋', 'after'], ['⠁⠉', 'according'], ['⠁⠃', 'about']]
    for word in shortform_words:
        word_length = len(word[0])
        word_matches = re.finditer(word[0], new_character_string)
        word_match_indices = [match.start() for match in word_matches]
        for i in range(len(word_match_indices)-1, -1, -1):
            #"word_match_indices[i] == len(new_character_string) - (word_length + 1)"
            #means that there is only one braille character after the "word[0]" match.
            #This is necessary, as an error would be raised if we were to look two
            #characters ahead. "word_match_indices[i] + word_length" is looking at
            #the braille character directly following the "word[0]" match. If there
            #is only one braille character after the "word[0]" match and that braille
            #character is either an empty braille cell (u"\u2800"), hyphen ("⠤"),
            #period ("⠲"), apostrophe ("⠄"), comma ("⠂"), colon ("⠒"), semicolon ("⠆")
            #question mark ("⠦"), exclamation mark ("⠖") or closing double quote ("⠴"),
            #then "word[0]" meets the requirements to be free standing on its right side.
            #We then proceed to look at its left side (before it) to ensure that it is
            #really free standing.
            if (word_match_indices[i] == len(new_character_string) - (word_length + 1) and
            new_character_string[word_match_indices[i] + word_length] in
            [u"\u2800", "⠤", "⠲", "⠄", "⠂", "⠒", "⠆", "⠦", "⠖", "⠴"]):
                #Now looking at the characters before the "word[0]" match. If there
                #are no braille characters before the start of "word[0]" and the conditions
                #in the parent "if" statement are met, than the shortform word is freestanding
                #and the substitution takes place.
                if word_match_indices[i] == 0:
                    new_character_string = word[1] + new_character_string[word_match_indices[i] + word_length:]
                #If there is only one braille character before the start of "word[0]",
                #and that character is either an empty braille cell (u"\u2800"), a
                #hyphen ("⠤"), a capitalization symbol ("⠠") or a double opening
                #quote ("⠦"), then the substitution of the shortform word "word[0]"
                #can take place, as "word[0]" stands alone:
                elif (word_match_indices[i] == 1 and
                new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"]):
                    new_character_string = (new_character_string[:word_match_indices[i]]
                    + word[1] + new_character_string[word_match_indices[i] + word_length:])
                #If there are two braille characters before the start of "word[0]", and
                #those characters are either an empty braille cell (u"\u2800"), hyphen
                #("⠤" or dash symbols that end with "⠤", such as minus sign ("⠐⠤"),
                #dash/en dash("⠠⠤") or underscore ("⠨⠤")), capitalization symbol ("⠠"),
                #opening single ("⠠⠦") or double ("⠦", "⠘⠦", "⠸⠦") quotes, any
                #typeform indicators for symbols, words or passages written in
                #italics ("⠨⠆", "⠨⠂", "⠨⠶"), bold ("⠘⠆", "⠘⠂", "⠘⠶"),
                #underline ("⠸⠆", "⠸⠂", "⠸⠶") or script ("⠈⠆", "⠈⠂", "⠈⠶"),
                #opening parenthesis ("⠐⠣"), square bracket ("⠨⠣") or curly
                #bracket ("⠸⠣"), then the substitution of the shortform
                #word "word[0]" can take place, as "word[0]" stands alone.
                #The en dash and underscore are covered in looking or the "⠤"
                #character preceding the "⠠⠴" match, and so are not included
                #in the list of two braille characters.
                elif (word_match_indices[i] == 2 and
                (new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                    new_character_string = (new_character_string[:word_match_indices[i]]
                    + word[1] + new_character_string[word_match_indices[i] + word_length:])
                #If the start of "word[0]" is located at least three braille characters from
                #the start of "new_character_string", and that word[0] is flanked either by
                #an empty braille cell (u"\u2800") or a hyphen ("⠤" or dash symbols that end
                #with "⠤" such as minus sign ("⠐⠤"), dash/en dash("⠠⠤"), long dash/em dash("⠐⠠⠤"),
                #or underscore ("⠨⠤")), capitalization symbol ("⠠"), opening single ("⠠⠦")
                #or double ("⠦", "⠘⠦", "⠸⠦") quotes, any typeform indicators for symbols,
                #words or passages written in italics ("⠨⠆", "⠨⠂", "⠨⠶"), bold ("⠘⠆", "⠘⠂", "⠘⠶"),
                #underline ("⠸⠆", "⠸⠂", "⠸⠶") or script ("⠈⠆", "⠈⠂", "⠈⠶"),
                #opening parenthesis ("⠐⠣", "⠠⠐⠣"), square bracket ("⠨⠣", "⠠⠨⠣") or curly
                #bracket ("⠸⠣", "⠠⠸⠣"), then the substitution of the shortform word "word[0]"
                #can take place, as "word[0]" stands alone. The em dash, en dash and underscore
                #are covered in looking for the "⠤" character preceding the "⠠⠴" match, and so
                #are not included in the list of two and three braille characters.
                elif (word_match_indices[i] >= 3 and
                (new_character_string[word_match_indices[i]-3:word_match_indices[i]] in
                ["⠠⠐⠣", "⠠⠨⠣", "⠠⠸⠣"] or
                new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                    new_character_string = (new_character_string[:word_match_indices[i]]
                    + word[1] + new_character_string[word_match_indices[i] + word_length:])
            #"word_match_indices[i] == len(new_character_string) - (word_length + 2)"
            #means that there are only two braille characters after the "word[0]" match.
            #This is necessary, as an error would be raised if we were to look three
            #characters ahead. If word[0] is flanked to the right by two braille characters
            #consisting of either closing single ("⠠⠴") or double ("⠘⠴", "⠸⠴") quotes,
            #closing parenthesis ("⠐⠜"), or square ("⠨⠜") or curly ("⠸⠜") brackets,
            #minus sign ("⠐⠤", which some people could mistakenly use as a hyphen),
            #en-dash ("⠠⠤"), underscore ("⠨⠤") or the terminators for passages or words
            #written in italics ("⠨⠄"), bold ("⠘⠄"), underline ("⠸⠄") or script ("⠈⠄"),
            #then then "word[0]" meets the requirements to be free standing on its right side.
            #We then proceed to look at its left side (before it) to ensure that it is
            #really free standing.
    
            #Alternatively, if the character direcly after word[0] is either an empty
            #braille cell (u"\u2800"), hyphen ("⠤"), period ("⠲"), apostrophe ("⠄"),
            #comma ("⠂"), colon ("⠒"), semicolon ("⠆") question mark ("⠦"),
            #exclamation mark ("⠖") or closing double quote ("⠴"), then "word[0]"
            #meets the requirements to be free standing on its right side. We then
            #proceed to look at its left side (before it) to ensure that it is
            #really free standing.
            elif (word_match_indices[i] == len(new_character_string) - (word_length + 2) and
            (new_character_string[word_match_indices[i] + word_length:word_match_indices[i] + word_length + 2] in
            ["⠠⠴", "⠘⠴", "⠸⠴", "⠐⠜", "⠨⠜", "⠸⠜", "⠐⠤", "⠠⠤", "⠨⠤", "⠨⠄", "⠘⠄", "⠸⠄", "⠈⠄"] or
            new_character_string[word_match_indices[i] + word_length] in
            [u"\u2800", "⠤", "⠲", "⠄", "⠂", "⠒", "⠆", "⠦", "⠖", "⠴"])):
                if word_match_indices[i] == 0:
                    new_character_string = word[1] + new_character_string[word_match_indices[i] + word_length:]
                elif (word_match_indices[i] == 1 and
                new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"]):
                    new_character_string = (new_character_string[:word_match_indices[i]]
                    + word[1] + new_character_string[word_match_indices[i] + word_length:])
                elif (word_match_indices[i] == 2 and
                (new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                 "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                    new_character_string = (new_character_string[:word_match_indices[i]]
                    + word[1] + new_character_string[word_match_indices[i] + word_length:])
                elif (word_match_indices[i] >= 3 and
                (new_character_string[word_match_indices[i]-3:word_match_indices[i]] in
                ["⠠⠐⠣", "⠠⠨⠣", "⠠⠸⠣"] or
                new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                    new_character_string = (new_character_string[:word_match_indices[i]]
                    + word[1] + new_character_string[word_match_indices[i] + word_length:])
    
            #Looking at up to three braille cells following the "word[0]" match, hence the
            #"word_match_indices[i] <= len(new_character_string) - (word_length +3)".
    
            #If word[0] is flanked to the right by three braille characters making up either
            #a multi-line closing parenthesis ("⠠⠐⠜"), square ("⠠⠨⠜") or curly ("⠠⠸⠜") bracket or
            #an em-dash ("⠐⠠⠤"), then then "word[0]" meets the requirements to be free standing
            #on its right side. We then proceed to look at its left side (before it) to ensure
            #that it is really free standing.
    
            #On the other hand, if word[0] is flanked to the right by two braille characters
            #consisting of either closing single ("⠠⠴") or double ("⠘⠴", "⠸⠴") quotes,
            #closing parenthesis ("⠐⠜"), or square ("⠨⠜") or curly ("⠸⠜") brackets,
            #minus sign ("⠐⠤", which some people could mistakenly use as a hyphen),
            #en-dash ("⠠⠤"), underscore ("⠨⠤") or the terminators for passages or words
            #written in italics ("⠨⠄"), bold ("⠘⠄"), underline ("⠸⠄") or script ("⠈⠄"),
            #then then "word[0]" meets the requirements to be free standing on its right side.
            #We then proceed to look at its left side (before it) to ensure that it is
            #really free standing.
    
            #Alternatively, if the character direcly after word[0] is either an empty
            #braille cell (u"\u2800"), hyphen ("⠤"), period ("⠲"), apostrophe ("⠄"),
            #comma ("⠂"), colon ("⠒"), semicolon ("⠆") question mark ("⠦"),
            #exclamation mark ("⠖") or closing double quote ("⠴"), then "word[0]"
            #meets the requirements to be free standing on its right side. We then
            #proceed to look at its left side (before it) to ensure that it is
            #really free standing.
            elif (word_match_indices[i] <= len(new_character_string) - (word_length +3) and
            (new_character_string[word_match_indices[i] + word_length:word_match_indices[i] + word_length +3] in
            ["⠠⠐⠜", "⠠⠨⠜", "⠠⠸⠜", "⠐⠠⠤"] or
            new_character_string[word_match_indices[i] + word_length:word_match_indices[i] + word_length + 2] in
            ["⠠⠴", "⠘⠴", "⠸⠴", "⠐⠜", "⠨⠜", "⠸⠜", "⠐⠤", "⠠⠤", "⠨⠤", "⠨⠄", "⠘⠄", "⠸⠄", "⠈⠄"] or
            new_character_string[word_match_indices[i] + word_length] in
            [u"\u2800", "⠤", "⠲", "⠄", "⠂", "⠒", "⠆", "⠦", "⠖", "⠴"])):
                if word_match_indices[i] == 0:
                    new_character_string = word[1] + new_character_string[word_match_indices[i] + word_length:]
                elif (word_match_indices[i] == 1 and
                new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"]):
                    new_character_string = (new_character_string[:word_match_indices[i]]
                    + word[1] + new_character_string[word_match_indices[i] + word_length:])
                elif (word_match_indices[i] == 2 and
                (new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                    new_character_string = (new_character_string[:word_match_indices[i]]
                    + word[1] + new_character_string[word_match_indices[i] + word_length:])
                elif (word_match_indices[i] >= 3 and
                (new_character_string[word_match_indices[i]-3:word_match_indices[i]] in
                ["⠠⠐⠣", "⠠⠨⠣", "⠠⠸⠣"] or
                new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                    new_character_string = (new_character_string[:word_match_indices[i]]
                    + word[1] + new_character_string[word_match_indices[i] + word_length:])
    
    
    #All following words need to stand alone in order to be transcribed to their printed English form.
    #The code is therefore largely the same as the one used for "shortform_words". However, since the
    #"⠆" symbol matching the lower groupsign "be" is also the second character in all typeform symbol
    #indicators, only the "word[0]" matches that are not preceded by the first character of the different
    #typeform indicators will be considered. The same goes for the "⠶" symbol matching the lower wordsign
    #"were", which is also the second character in all typeform passage indicators.
    be_were_words = [['⠆⠽', 'beyond'], ['⠆⠞', 'between'], ['⠆⠎', 'beside'], ['⠆⠝', 'beneath'],
    ['⠆⠇', 'below'], ['⠆⠓', 'behind'], ['⠆⠋', 'before'], ['⠆⠉', 'because'], ["⠶", "were"]]
    for word in be_were_words:
        word_length = len(word[0])
        word_matches = re.finditer(word[0], new_character_string)
        word_match_indices = [match.start() for match in word_matches]
        for i in range(len(word_match_indices)-1, -1, -1):
            if (word_match_indices[i] == len(new_character_string) - (word_length + 1) and
            new_character_string[word_match_indices[i] + word_length] in
            [u"\u2800", "⠤", "⠲", "⠄", "⠂", "⠒", "⠆", "⠦", "⠖", "⠴"]):
                if word_match_indices[i] == 0:
                    new_character_string = word[1] + new_character_string[word_match_indices[i] + word_length:]
                #Since the "⠆" symbol matching the lower groupsign "be" is also the second character
                #in all typeform symbol indicators, only the "word[0]" matches that are not preceded
                #by the first character of the different typeform indicators will be considered.
                elif (word_match_indices[i] > 0 and new_character_string[word_match_indices[i]-1] not in
                ["⠨", "⠘", "⠸", "⠈"]):
                    if (word_match_indices[i] == 1 and
                    new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"]):
                        new_character_string = (new_character_string[:word_match_indices[i]]
                        + word[1] + new_character_string[word_match_indices[i] + word_length:])
                    elif (word_match_indices[i] == 2 and
                    (new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                    ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                    "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                    new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                        new_character_string = (new_character_string[:word_match_indices[i]]
                        + word[1] + new_character_string[word_match_indices[i] + word_length:])
                    elif (word_match_indices[i] >= 3 and
                    (new_character_string[word_match_indices[i]-3:word_match_indices[i]] in
                    ["⠠⠐⠣", "⠠⠨⠣", "⠠⠸⠣"] or
                    new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                    ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                    "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                    new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                        new_character_string = (new_character_string[:word_match_indices[i]]
                        + word[1] + new_character_string[word_match_indices[i] + word_length:])
            elif (word_match_indices[i] == len(new_character_string) - (word_length + 2) and
            (new_character_string[word_match_indices[i] + word_length:word_match_indices[i] + word_length + 2] in
            ["⠠⠴", "⠘⠴", "⠸⠴", "⠐⠜", "⠨⠜", "⠸⠜", "⠐⠤", "⠠⠤", "⠨⠤", "⠨⠄", "⠘⠄", "⠸⠄", "⠈⠄"] or
            new_character_string[word_match_indices[i] + word_length] in
            [u"\u2800", "⠤", "⠲", "⠄", "⠂", "⠒", "⠆", "⠦", "⠖", "⠴"])):
                if word_match_indices[i] == 0:
                    new_character_string = word[1] + new_character_string[word_match_indices[i] + word_length:]
                #Since the "⠆" symbol matching the lower groupsign "be" is also the second character
                #in all typeform symbol indicators, only the "word[0]" matches that are not preceded
                #by the first character of the different typeform indicators will be considered.
                elif (word_match_indices[i] > 0 and new_character_string[word_match_indices[i]-1] not in
                ["⠨", "⠘", "⠸", "⠈"]):
                    if (word_match_indices[i] == 1 and
                    new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"]):
                        new_character_string = (new_character_string[:word_match_indices[i]]
                        + word[1] + new_character_string[word_match_indices[i] + word_length:])
                    elif (word_match_indices[i] == 2 and
                    (new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                    ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                    "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                    new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                        new_character_string = (new_character_string[:word_match_indices[i]]
                        + word[1] + new_character_string[word_match_indices[i] + word_length:])
                    elif (word_match_indices[i] >= 3 and
                    (new_character_string[word_match_indices[i]-3:word_match_indices[i]] in
                    ["⠠⠐⠣", "⠠⠨⠣", "⠠⠸⠣"] or
                    new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                    ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                    "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                    new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                        new_character_string = (new_character_string[:word_match_indices[i]]
                        + word[1] + new_character_string[word_match_indices[i] + word_length:])
            elif (word_match_indices[i] <= len(new_character_string) - (word_length +3) and
            (new_character_string[word_match_indices[i] + word_length:word_match_indices[i] + word_length +3] in
            ["⠠⠐⠜", "⠠⠨⠜", "⠠⠸⠜", "⠐⠠⠤"] or
            new_character_string[word_match_indices[i] + word_length:word_match_indices[i] + word_length + 2] in
            ["⠠⠴", "⠘⠴", "⠸⠴", "⠐⠜", "⠨⠜", "⠸⠜", "⠐⠤", "⠠⠤", "⠨⠤", "⠨⠄", "⠘⠄", "⠸⠄", "⠈⠄"] or
            new_character_string[word_match_indices[i] + word_length] in
            [u"\u2800", "⠤", "⠲", "⠄", "⠂", "⠒", "⠆", "⠦", "⠖", "⠴"])):
                if word_match_indices[i] == 0:
                    new_character_string = word[1] + new_character_string[word_match_indices[i] + word_length:]
                #Since the "⠆" symbol matching the lower groupsign "be" is also the second character
                #in all typeform symbol indicators, only the "word[0]" matches that are not preceded
                #by the first character of the different typeform indicators will be considered.
                elif (word_match_indices[i] > 0 and new_character_string[word_match_indices[i]-1] not in
                ["⠨", "⠘", "⠸", "⠈"]):
                    if (word_match_indices[i] == 1 and
                    new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"]):
                        new_character_string = (new_character_string[:word_match_indices[i]]
                        + word[1] + new_character_string[word_match_indices[i] + word_length:])
                    elif (word_match_indices[i] == 2 and
                    (new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                    ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                    "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                    new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                        new_character_string = (new_character_string[:word_match_indices[i]]
                        + word[1] + new_character_string[word_match_indices[i] + word_length:])
                    elif (word_match_indices[i] >= 3 and
                    (new_character_string[word_match_indices[i]-3:word_match_indices[i]] in
                    ["⠠⠐⠣", "⠠⠨⠣", "⠠⠸⠣"] or
                    new_character_string[word_match_indices[i]-2:word_match_indices[i]] in
                    ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
                    "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
                    new_character_string[word_match_indices[i]-1] in [u"\u2800", "⠤", "⠦", "⠠"])):
                        new_character_string = (new_character_string[:word_match_indices[i]]
                        + word[1] + new_character_string[word_match_indices[i] + word_length:])
    
    
    #The two capitalized braille lower wordsigns "⠠⠦ , His" and "⠠⠴, Was" could be confused with
    #the opening ("‘") and closing ("’") single quotes, respectively. Therefore, the following code
    #is intended to disambiguate these different meanings of the same braille characters. It is
    #important to perform the substitutions of "Was" before "His", because in the unlikely event
    #that the braille equivalent of "‘Was’," ("⠠⠦⠠⠴⠠⠴") needs to be transcribed to printed English,
    #using the reverse order would give "His’’".
    
    #If the character before the "⠠⠴" match is an empty braille cell (u"\u2800") or one of the following:
    #hyphen ("⠤" or dash symbols that end with "⠤" such as minus sign ("⠐⠤"), dash/en dash("⠠⠤"),
    #long dash/em dash("⠐⠠⠤"), or underscore ("⠨⠤")), opening single ("⠠⠦") or double ("⠘⠦", "⠸⠦") quotes,
    #any typeform indicators for symbols, words or passages written in italics ("⠨⠆", "⠨⠂", "⠨⠶"),
    #bold ("⠘⠆", "⠘⠂", "⠘⠶"), underline ("⠸⠆", "⠸⠂", "⠸⠶") or script ("⠈⠆", "⠈⠂", "⠈⠶"), opening
    #parenthesis ("⠐⠣", "⠠⠐⠣"), square bracket ("⠨⠣", "⠠⠨⠣") or curly bracket ("⠸⠣", "⠠⠸⠣"),
    #it can be concluded that the "⠠⠴" match stands for "Was", as these would not be found before
    #a closing single quotation mark "’". The substitutions are done in reverse order (starting from the end)
    #in order to avoid staggering the indices.
    
    #Unlike the code above, the capitalization symbol ("⠠") isn't included in the following lines of code:
    #"new_character_string[capitalized_was_match_indices[i]-1] in [u"\u2800", "⠤"], because there wouldn't
    #be a capitalization symbol preceding either "Was" or a closing single quote ("’"). Furthermore, the
    #closing double quotes braille symbol ("⠴") isn't included either, as it can also correspond to a
    #question mark ("?") and otherwise "Was" would follow question marks instead of a closing single quote ("’").
    
    capitalized_was_matches = re.finditer("⠠⠴", new_character_string)
    capitalized_was_match_indices = [match.start() for match in capitalized_was_matches]
    for i in range(len(capitalized_was_match_indices)-1, -1, -1):
        #If there are no braille characters before the start of the "⠠⠴" match, then we
        #assume that the document starts with "Was" and not a single closing quote "’":
        if capitalized_was_match_indices[i] == 0:
            new_character_string = "Was" + new_character_string[capitalized_was_match_indices[i]+2:]
        elif (capitalized_was_match_indices[i] == 1 and
        new_character_string[capitalized_was_match_indices[i]-1] in [u"\u2800", "⠤"]):
            new_character_string = (new_character_string[:capitalized_was_match_indices[i]]
            + "Was" + new_character_string[capitalized_was_match_indices[i]+2:])
        elif (capitalized_was_match_indices[i] == 2 and
        (new_character_string[capitalized_was_match_indices[i]-2:capitalized_was_match_indices[i]] in
        ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
        "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
        new_character_string[capitalized_was_match_indices[i]-1] in [u"\u2800", "⠤"])):
            new_character_string = (new_character_string[:capitalized_was_match_indices[i]]
            + "Was" + new_character_string[capitalized_was_match_indices[i]+2:])
        elif (capitalized_was_match_indices[i] >= 3 and
        (new_character_string[capitalized_was_match_indices[i]-3:capitalized_was_match_indices[i]] in
        ["⠠⠐⠣", "⠠⠨⠣", "⠠⠸⠣"] or
        new_character_string[capitalized_was_match_indices[i]-2:capitalized_was_match_indices[i]] in
        ["⠠⠦", "⠘⠦", "⠸⠦", "⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶",
        "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶", "⠐⠣", "⠨⠣", "⠸⠣"] or
        new_character_string[capitalized_was_match_indices[i]-1] in [u"\u2800", "⠤"])):
            new_character_string = (new_character_string[:capitalized_was_match_indices[i]]
            + "Was" + new_character_string[capitalized_was_match_indices[i]+2:])
        else:
            new_character_string = (new_character_string[:capitalized_was_match_indices[i]]
            + "’" + new_character_string[capitalized_was_match_indices[i]+2:])
    
    #If the character following the "⠠⠦" match is an empty braille cell (u"\u2800") or one of the following:
    #hyphen ("⠤"), period or first character of ellipsis ("⠲"), comma ("⠂"), colon ("⠒"), semicolon ("⠆"),
    #question mark ("⠦"), exclamation mark ("⠖"), closing single ("⠠⠴") or double ("⠴" or "⠘⠴" or "⠸⠴") quotes,
    #closing parenthesis ("⠐⠜" or "⠠⠐⠜"), closing square bracket ("⠨⠜" or "⠠⠨⠜"),
    #closing curly bracket ("⠸⠜" or "⠠⠸⠜"), minus sign ("⠐⠤"), dash/en dash("⠠⠤"), long dash/em dash("⠐⠠⠤"),
    #underscore ("⠨⠤") or the terminator symbols for passages written in italics ("⠨⠄"), bold ("⠘⠄"), underline ("⠸⠄")
    #or script ("⠈⠄"), it can be concluded that the "⠠⠦" match stands for "His",
    #as these would not be found after an opening single quotation mark "‘". The substitutions are done in reverse order
    #(starting from the end) in order to avoid staggering the indices.
    capitalized_his_matches = re.finditer("⠠⠦", new_character_string)
    capitalized_his_match_indices = [match.start() for match in capitalized_his_matches]
    for i in range(len(capitalized_his_match_indices)-1, -1, -1):
        #"capitalized_his_match_indices[i] == len(new_character_string)-3" means that there
        #is only one braille character after the "⠠⠦" match (3 corresponds to the length
        #of the "⠠⠦" match (2), plus 1). This is necessary, as an error would be raised if
        #we were to look two characters ahead. "capitalized_his_match_indices[i]+2" is
        #looking at the braille character directly following the "⠠⠦" match. "’" is added
        #as a possibility following a "⠠⠦" match for it to be transcribed to "His", as
        #some "’" characters might have been introduced earlier (either in dealing with the
        #"⠠⠴"/Was matches or the grade I passages.)
        if (capitalized_his_match_indices[i] == len(new_character_string)-3 and
        new_character_string[capitalized_his_match_indices[i]+2] in
        [u"\u2800", "⠤", "⠲", "⠂", "⠒", "⠆", "⠦", "⠖", "⠴", "’"]):
            new_character_string = (new_character_string[:capitalized_his_match_indices[i]]
            + "His" + new_character_string[capitalized_his_match_indices[i]+2:])
        #"capitalized_his_match_indices[i] == len(new_character_string)-4" means that there
        #are only two braille characters after the "⠠⠦" match (4 corresponds to the length
        #of the "⠠⠦" match (2), plus 2). This is necessary, as an error would be raised
        #if we were to look three characters ahead. Here, the en-dash ("⠠⠤"), minus-sign ("⠐⠤"),
        #which some people might use mistakenly instead of a hyphen) and underscore ("⠨⠤")
        #must all be screened for, as we are looking to the right of the "⠠⠦" match and the
        #first character for all these dashes is different.
        elif (capitalized_his_match_indices[i] == len(new_character_string)-4 and
        (new_character_string[capitalized_his_match_indices[i]+2:capitalized_his_match_indices[i]+4] in
        ["⠠⠴", "⠘⠴", "⠸⠴", "⠐⠜", "⠨⠜", "⠸⠜", "⠐⠤", "⠠⠤", "⠨⠤", "⠨⠄", "⠘⠄", "⠸⠄", "⠈⠄"] or
        new_character_string[capitalized_his_match_indices[i]+2] in
        [u"\u2800", "⠤", "⠲", "⠂", "⠒", "⠆", "⠦", "⠖", "⠴", "’"])):
            new_character_string = (new_character_string[:capitalized_his_match_indices[i]]
            + "His" + new_character_string[capitalized_his_match_indices[i]+2:])
        #Looking at up to three braille cells following the "⠠⠦" match, hence the
        #"capitalized_his_match_indices[i] <= len(new_character_string)-5" (5 corresponds to
        #the length of the "⠠⠦" match (2), plus 3). Here, the em-dash ("⠐⠠⠤"), en-dash ("⠠⠤"),
        #minus-sign ("⠐⠤"), which some people might use mistakenly instead of a hyphen) and
        #underscore ("⠨⠤") must all be screened for, as we are looking to the right of the "⠠⠦"
        #match and the first character for all these dashes is different.
        elif (capitalized_his_match_indices[i] <= len(new_character_string)-5 and
        (new_character_string[capitalized_his_match_indices[i]+2:capitalized_his_match_indices[i]+5] in
        ["⠠⠐⠜", "⠠⠨⠜", "⠠⠸⠜", "⠐⠠⠤"] or
        new_character_string[capitalized_his_match_indices[i]+2:capitalized_his_match_indices[i]+4] in
        ["⠠⠴", "⠘⠴", "⠸⠴", "⠐⠜", "⠨⠜", "⠸⠜", "⠐⠤", "⠠⠤", "⠨⠤", "⠨⠄", "⠘⠄", "⠸⠄", "⠈⠄"] or
        new_character_string[capitalized_his_match_indices[i]+2] in
        [u"\u2800", "⠤", "⠲", "⠂", "⠒", "⠆", "⠦", "⠖", "⠴", "’"])):
            new_character_string = (new_character_string[:capitalized_his_match_indices[i]]
            + "His" + new_character_string[capitalized_his_match_indices[i]+2:])
        else:
            new_character_string = (new_character_string[:capitalized_his_match_indices[i]]
            + "‘" + new_character_string[capitalized_his_match_indices[i]+2:])
    
    #Disambiguation of "⠄","’":
    #Since the "⠄" symbol for the apostrophe is also the second character in all
    #grade I/capitalization and typeform terminators, only the "⠄" matches that
    #are not preceded by the first character of the different terminators will
    #be transcribed to the apostrophe.
    apostrophe_matches = re.finditer("⠄", new_character_string)
    apostrophe_match_indices = [match.start() for match in apostrophe_matches]
    for i in range(len(apostrophe_match_indices)-1, -1, -1):
        if (apostrophe_match_indices[i] > 0 and new_character_string[apostrophe_match_indices[i]-1] not in
        ["⠠", "⠰", "⠨", "⠘", "⠸", "⠈"]):
            new_character_string = (new_character_string[:apostrophe_match_indices[i]]
            + "’" + new_character_string[apostrophe_match_indices[i]+1:])
    
    #The multicharacter braille words in "braille_combinations" are sorted by
    #decreasing braille character length. In the "braille_combinations" list,
    #I mapped the opening and closing transcriber's notes to an opening and
    #closing square bracket, respectively (["⠈⠨⠣", "["], ["⠈⠨⠜", "]"]) Also,
    #users should be notified to only use directional quotes, as the non-directional
    #double quote ('⠠⠶', '"') could be transcribed by the code to the capitalized
    #form of "were". While the RTF escapes are needed to ensure good output results,
    #the list "braille_combinations" with the actual symbols is also provided in
    #commented form for better readability:
    
    # braille_combinations = [['⠐⠠⠤', '—'], ['⠲⠲⠲', '…'], ['⠈⠨⠣', '['],
    #['⠈⠨⠜', ']'], ['⠈⠠⠹', '†'], ['⠈⠠⠻', '‡'], ['⠠⠐⠣', '('], ['⠠⠐⠜', ')'],
    #['⠠⠨⠣', '['], ['⠠⠨⠜', ']'], ['⠠⠸⠣', '{'], ['⠠⠸⠜', '}'], ['⠨⠑', 'ance'],
    #['⠸⠉', 'cannot'], ['⠐⠡', 'character'], ['⠐⠙', 'day'], ['⠐⠑', 'ever'],
    # ['⠐⠋', 'father'], ['⠸⠓', 'had'], ['⠐⠓', 'here'], ['⠐⠅', 'know'], ['⠐⠇', 'lord'],
    #['⠸⠍', 'many'], ['⠐⠍', 'mother'], ['⠐⠝', 'name'], ['⠐⠕', 'one'], ['⠨⠙', 'ound'],
    #['⠨⠞', 'ount'], ['⠐⠳', 'ought'], ['⠐⠏', 'part'], ['⠐⠟', 'question'], ['⠐⠗', 'right'],
    #['⠐⠎', 'some'], ['⠸⠎', 'spirit'], ['⠸⠮', 'their'], ['⠐⠮', 'there'], ['⠘⠮', 'these'],
    # ['⠘⠹', 'those'], ['⠐⠹', 'through'], ['⠐⠞', 'time'], ['⠐⠥', 'under'], ['⠘⠥', 'upon'],
    # ['⠐⠱', 'where'], ['⠘⠱', 'whose'], ['⠘⠺', 'word'], ['⠐⠺', 'work'], ['⠸⠺', 'world'],
    #['⠐⠽', 'young'], ['⠐⠖', '+'], ['⠐⠤', '-'], ['⠐⠦', '✕'], ['⠐⠲', '⋅'], ['⠐⠌', '÷'],
    #['⠈⠜', '>'], ['⠈⠣', '<'], ['⠐⠶', '='], ['⠈⠉', '¢'], ['⠈⠎', '$'], ['⠈⠑', '€'],
    #['⠈⠇', '£'], ['⠶⠶', '″'], ['⠨⠴', '%'], ['⠘⠚', '°'], ['⠸⠪', '∠'], ['⠸⠹', '#'],
    #['⠈⠯', '&'], ['⠘⠉', '©'], ['⠘⠞', '™'], ['⠸⠲', '•'], ['⠈⠁', '@'], ['⠐⠔', '*'],
    #['⠠⠤', '—'], ['⠸⠌', '/'], ['⠸⠡', r'\\'], ['⠠⠦', '‘'], ['⠠⠴', '’'], ['⠐⠣', '('],
    #['⠐⠜', ')'], ['⠨⠣', '['], ['⠨⠜', ']'], ['⠸⠣', '{'], ['⠸⠜', '}'], ['⠈⠔', '∼'],
    #['⠐⠂', '〃'], ['⠘⠦', '“'], ['⠘⠴', '”'], ['⠘⠏', '¶'], ['⠘⠗', '®'], ['⠘⠎', '§'],
    #['⠨⠤', '_'], ['⠸⠦', '«'], ['⠸⠴', '»']]
    braille_combinations = [['⠐⠠⠤', "—"], ['⠲⠲⠲', '…'], ['⠈⠨⠣', '['],
    ['⠈⠨⠜', ']'], ['⠈⠠⠹', r"\'86"], ['⠈⠠⠻', r"\'87"], ['⠠⠐⠣', '('], ['⠠⠐⠜', ')'],
    ['⠠⠨⠣', '['], ['⠠⠨⠜', ']'], ['⠠⠸⠣', '{'], ['⠠⠸⠜', '}'], ['⠨⠑', 'ance'],
    ['⠸⠉', 'cannot'], ['⠐⠡', 'character'], ['⠐⠙', 'day'], ['⠐⠑', 'ever'],
    ['⠐⠋', 'father'], ['⠸⠓', 'had'], ['⠐⠓', 'here'], ['⠐⠅', 'know'], ['⠐⠇', 'lord'],
    ['⠸⠍', 'many'], ['⠐⠍', 'mother'], ['⠐⠝', 'name'], ['⠐⠕', 'one'], ['⠨⠙', 'ound'],
    ['⠨⠞', 'ount'], ['⠐⠳', 'ought'], ['⠐⠏', 'part'], ['⠐⠟', 'question'], ['⠐⠗', 'right'],
    ['⠐⠎', 'some'], ['⠸⠎', 'spirit'], ['⠸⠮', 'their'], ['⠐⠮', 'there'], ['⠘⠮', 'these'],
    ['⠘⠹', 'those'], ['⠐⠹', 'through'], ['⠐⠞', 'time'], ['⠐⠥', 'under'], ['⠘⠥', 'upon'],
    ['⠐⠱', 'where'], ['⠘⠱', 'whose'], ['⠘⠺', 'word'], ['⠐⠺', 'work'], ['⠸⠺', 'world'],
    ['⠐⠽', 'young'], ['⠐⠖', r"\'2b"], ['⠐⠤', "-"], ['⠐⠦', r"\'d7"], ['⠐⠲', r"\'b7"], ['⠐⠌', r"\'f7"],
    ['⠈⠜', r"\'3e"], ['⠈⠣', r"\'3c"], ['⠐⠶', r"\'3d"], ['⠈⠉', r"\'a2"], ['⠈⠎', r"\'24"], ['⠈⠑', r"\'80"],
    ['⠈⠇', r"\'a3"], ['⠶⠶', r"\'22"], ['⠨⠴', r"\'25"], ['⠘⠚', r"\'b0"], ['⠸⠪', '⠀angle⠀'], ['⠸⠹', r"\'23"],
    ['⠈⠯', r"\'26"], ['⠘⠉', r"\'a9"], ['⠘⠞', r"\'99"], ['⠸⠲', r"\'95"], ['⠈⠁', r"\'40"], ['⠐⠔', r"\'2a"],
    ['⠠⠤', "—"], ['⠸⠌', r"\'2f"], ['⠸⠡', r'\\'], ['⠠⠦', "‘"], ['⠠⠴', "’"], ['⠐⠣', '('],
    ['⠐⠜', ')'], ['⠨⠣', '['], ['⠨⠜', ']'], ['⠸⠣', '{'], ['⠸⠜', '}'], ['⠈⠔', r"\'98"],
    ['⠐⠂', r"\'22"], ['⠘⠦', '“'], ['⠘⠴', '”'], ['⠘⠏', r"\'b6"], ['⠘⠗', r"\'ae"], ['⠘⠎', r"\'a7"],
    ['⠨⠤', r"\'5f"], ['⠸⠦', '«'], ['⠸⠴', '»']]
    braille_combination_symbols = []
    for i in range(len(braille_combinations)):
        braille_combination_symbols.append(braille_combinations[i][0])
        new_character_string = re.sub(braille_combinations[i][0], braille_combinations[i][1], new_character_string)
    
    #Once that the multi-braille-character dashes (['⠐⠠⠤', "—"], ['⠠⠤', "—"],
    #['⠐⠤', "-"], ['⠨⠤', '_']) have been converted to their respective unicode
    #symbols in the "braille_combination_symbols" code above, the remaining
    #"⠤" may be converted into hyphens.
    new_character_string = new_character_string.replace("⠤", "-")
    
    #Disambiguation of lower wordsigns "his" and "was" with their associated punctuation marks:
    #The wordsigns "his" and "was" shouldn't be preceded or followed by a letter, while the punctuation marks
    #"?" and "”" need to be preceded either by a letter, "!",  "?", dashes when followed by '”' to indicate an
    #unfinished sentence in a dialogue ("—", "—", "_", "-") the second symbol of a typeform terminator ("⠄")
    #when typeform is used before "?" or '”', or a closing single quote ("’") followed by "”" in the event of
    #nested quotes. "⠦" also maps to the opening double quote "“" which should be followed by a letter (it will
    #be transcribed at the very end of the code and not covered in this section).
    lower_wordsigns = [[["⠦", "his"], ["⠦", "?"]], [["⠴", "was"], ["⠴", '”']]]
    for lower_wordsign in lower_wordsigns:
        lower_wordsign_matches = re.finditer(lower_wordsign[0][0], new_character_string)
        lower_wordsign_match_indices = [match.start() for match in lower_wordsign_matches]
        for i in range(len(lower_wordsign_match_indices)-1, -1, -1):
            #If the braille character is found at the very start of the document, it then cannot be a
            #closing punctuation mark such as "?" and "”" nor a lower wordsign "his" or "was", as these
            #would be capitalized (preceded by the "⠠" braille character) In the case of "⠦", this only
            #leaves the opening double quote "“", which will be transcribed later in the code.
            if lower_wordsign_match_indices[i] == 0:
                pass
            #If the preceding braille character is a letter, the second braille character of a typeform
            #terminator ("⠄") or one of the following: "!", "?", "’", "—", "—", "_", "-", then substitution
            #for the corresponding punctuation mark ("?" or "”", but not "“" (which is also encoded by
            #the "⠦" braille character, but will be dealt with later), as an opening double quotation
            #mark wouldn't be preceded by a letter) takes place.
            elif (new_character_string[lower_wordsign_match_indices[i]-1] in (braille_alphabet + ambiguous_characters +
            contraction_characters + ["⠄", "!", "?", "’", "—", "—", "_", "-"])):
                new_character_string = (new_character_string[:lower_wordsign_match_indices[i]]
                + lower_wordsign[1][1] + new_character_string[lower_wordsign_match_indices[i]+1:])
            #If the braille character is found at the very end of the document, it must be one of the
            #punctuation marks "?", "”", but not "“", which would be followed by a letter. The lower
            #wordsigns would be followed by a punctuation mark at the end of a document.
            elif lower_wordsign_match_indices[i] == len(new_character_string)-1:
                new_character_string = (new_character_string[:lower_wordsign_match_indices[i]]
                + lower_wordsign[1][1] + new_character_string[lower_wordsign_match_indices[i]+1:])
    
            #If there is only one character following the match and that this character is either a blank
            #braille cell (u"\u2800") or one of the following:  period or the first character of the
            #ellipsis ("⠲"), comma ("⠂"), colon ("⠒"), semicolon ("⠆"), question mark ("⠦"),
            #exclamation mark ("⠖"), closing double quotes ("⠴"), "—", "—", "-", "-", "_", "’",
            #")", "]", or "}", then the result could be the wordsign. The character before it will
            #need to be examined as well in the child "if" statement below. The following symbols
            #were also included in their unicode form in case some grade I passages that were dealt
            #with earlier included "⠦" or "⠴": '”', '»', "?", "!",  ".",  "…", ",", ":", ";".
            elif (lower_wordsign_match_indices[i] == len(new_character_string) - 2 and
            new_character_string[lower_wordsign_match_indices[i]+1] in
            [u"\u2800", "⠲", "⠂", "⠒", "⠆", "⠦", "⠖", "⠴", "—", "—", "-", "-", "_",
            "’", '”', '»', ")", "]", "}", "?", "!", ".",  "…", ",", ":", ";"]):
                #In addition to the conditions met in the parent "elif" statement, if the preceding character is
                #either an empty braille cell (u"\u2800"), some sort of dash/hyphen or an opening single ("‘") or
                #double quote ("⠦",'“', '«'), a capitalation symbol ("⠠") or one of the following: "(", "[", "{",
                #then it can be concluded that the wordsign stands alone.
                if (new_character_string[lower_wordsign_match_indices[i]-1] in
                [u"\u2800", "⠦", "⠠", "—", "—", "-", "-", "_", "‘", '“', '«', "(", "[", "{"]):
                    new_character_string = (new_character_string[:lower_wordsign_match_indices[i]]
                    + lower_wordsign[0][1] + new_character_string[lower_wordsign_match_indices[i]+1:])
            #If there is only one character following the match and that this character is either a blank
            #braille cell (u"\u2800") or one of the following:  period or the first character of the
            #ellipsis ("⠲"), comma ("⠂"), colon ("⠒"), semicolon ("⠆"), question mark ("⠦"),
            #exclamation mark ("⠖"), closing double quotes ("⠴"), "—", "—", "-", "-", "_", "’",
            #")", "]", "}", or the terminator symbols for passages written in italics ("⠨⠄"),
            #bold ("⠘⠄"), underline ("⠸⠄") or script ("⠈⠄"), then the result could be the wordsign.
            #The character before it will need to be examined as well in the child "if" statement below.
            #The following symbols were also included in their unicode form in case some grade I passages
            #that were dealt with earlier included "⠦" or "⠴": '”', '»', "?", "!",  ".",  "…", ",", ":", ";".
            elif (lower_wordsign_match_indices[i] <= len(new_character_string) - 3 and
            (new_character_string[lower_wordsign_match_indices[i]+1:lower_wordsign_match_indices[i]+3] in
            ["⠨⠄", "⠘⠄", "⠸⠄", "⠈⠄"] or
            new_character_string[lower_wordsign_match_indices[i]+1] in
            [u"\u2800", "⠲", "⠂", "⠒", "⠆", "⠦", "⠖", "⠴", "—", "—", "-", "-", "_",
            "’", '”', '»', ")", "]", "}", "?", "!", ".",  "…", ",", ":", ";"])):
                if (new_character_string[lower_wordsign_match_indices[i]-1] in
                [u"\u2800", "⠦", "⠠", "—", "—", "-", "-", "_", "‘", '“', '«', "(", "[", "{"]):
                    new_character_string = (new_character_string[:lower_wordsign_match_indices[i]]
                    + lower_wordsign[0][1] + new_character_string[lower_wordsign_match_indices[i]+1:])
    
    #Once the ambiguities realive to "⠦" have been addressed (["⠦", "his"], ["⠦", "?"]], see above),
    #the remaining "⠦" are converted to the opening double quotes '“'.
    new_character_string = new_character_string.replace("⠦", '“')
    
    #Disambiguation of lower groupsigns vs repeating letters:
    double_letter_lower_groupsigns = [[["⠆", "bb"], ["⠆", ";"]], [["⠒", "cc"], ["⠒", ":"]], [["⠖", "ff"],
    ["⠖", "!"]], [["⠶", "gg"], ["⠶", r"\'27"]], [["⠂", "ea"], ["⠂", ","]]]
    for double_letter in double_letter_lower_groupsigns:
        double_letter_matches = re.finditer(double_letter[0][0], new_character_string)
        double_letter_match_indices = [match.start() for match in double_letter_matches]
        for i in range(len(double_letter_match_indices)-1, -1, -1):
            #If the match isn't situated at the very start nor at the very end of the document (neither the
            #punctuation marks ";", ":", "!", prime and ",", nor the repeating letters would be found there)
            #and if the preceding braille character is a either letter, "}" (for RTF commands that would
            #close with "}") or "⠄" (which is the second character in all typeform terminators), then the
            #following character will be inspected. If it is also a letter, then the braille character will
            #be replaced by the lower groupsign with repeating letters.
            #The "⠄" is in case there is a bold, italics, underline or script terminator before the punctuation mark.
            #The "}" is in case there is a closing "}" delimiting the end of a RTF command, before the punctuation mark.
            #The same goes for "), ], ?, !", which could precede the punctuation mark.
            if (double_letter_match_indices[i] != 0 and
            double_letter_match_indices[i] != len(new_character_string) - 1):
                if (new_character_string[double_letter_match_indices[i]-1] in
                (braille_alphabet + contraction_characters) and
                new_character_string[double_letter_match_indices[i]+1] in
                (braille_alphabet + contraction_characters)):
                    new_character_string = (new_character_string[:double_letter_match_indices[i]]
                    + double_letter[0][1] + new_character_string[double_letter_match_indices[i]+1:])
                #If there is a letter before the braille character but not after it, it will be changed
                #for the punctuation mark (";", ":", "!", prime and ",", as the third possible outcome for
                #"⠆", "⠶" and "⠒" cannot be preceded by a letter (lower wordsigns "be" and "were" and
                #lower groupsign "con", respectively).)
                elif (new_character_string[double_letter_match_indices[i]-1] in
                (braille_alphabet + contraction_characters + ["⠄", ")", "}", "]", "?", "!"])):
                        new_character_string = (new_character_string[:double_letter_match_indices[i]]
                        + double_letter[1][1] + new_character_string[double_letter_match_indices[i]+1:])
    
    #Disambiguation of lower groupsign "dis" with its associated punctuation mark ".":
    #The groupsign "dis" (which must begin a word) should only be preceded by an empty
    #braille cell (u"\u2800"), capitalization braille symbol ("⠠") or one of the following:
    #"—", "—", "-", "-", "_", "‘", '“', '«', "(", "[", "{". On the other hand, the period (".")
    #should only be preceded by a letter.
    dis_period = ["⠲", "dis"], ["⠲", "."]
    dis_period_matches = re.finditer(dis_period[0][0], new_character_string)
    dis_period_match_indices = [match.start() for match in dis_period_matches]
    for i in range(len(dis_period_match_indices)-1, -1, -1):
        #If the braille character is found at the very start of the document, it then cannot
        #be a closing punctuation mark such as ".".
        if dis_period_match_indices[i] == 0:
            new_character_string = (new_character_string[:dis_period_match_indices[i]]
            + dis_period[0][1] + new_character_string[dis_period_match_indices[i]+1:])
        #If the preceding braille character is a letter is an empty braille cell (u"\u2800"),
        #capitalization braille symbol ("⠠") or one of the following: "—", "—", "-", "-", "_",
        #"‘", '“', '«', "(", "[", "{", then substitution for "dis" takes place.
        elif (dis_period_match_indices[i] == 1 and
        new_character_string[dis_period_match_indices[i]-1] in
        [u"\u2800", "⠠", "—", "—", "-", "-", "_", "‘", '“', '«', "(", "[", "{"]):
            new_character_string = (new_character_string[:dis_period_match_indices[i]]
            + dis_period[0][1] + new_character_string[dis_period_match_indices[i]+1:])
        elif (dis_period_match_indices[i] >= 2 and
        (new_character_string[dis_period_match_indices[i]-2:dis_period_match_indices[i]] in
        ["⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶", "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶"] or
        new_character_string[dis_period_match_indices[i]-1] in
        [u"\u2800", "⠠", "—", "—", "-", "-", "_", "‘", '“', '«', "(", "[", "{"])):
            new_character_string = (new_character_string[:dis_period_match_indices[i]]
            + dis_period[0][1] + new_character_string[dis_period_match_indices[i]+1:])
        #Otherwise, "." is substituted for the braille character.
        else:
            new_character_string = (new_character_string[:dis_period_match_indices[i]]
            + dis_period[1][1] + new_character_string[dis_period_match_indices[i]+1:])
    
    #Disambiguation for the wordsigns and their corresponding groupsign. If there is at least one letter
    #on any side of the braille character, then the substitution is made for the groupsign, as the
    #wordsigns must stand alone.
    wordsigns = [[["⠡", "child"], ["⠡", "ch"]], [["⠩", "shall"], ["⠩", "sh"]], [["⠹", "this"],
    ["⠹", "th"]], [["⠱", "which"], ["⠱", "wh"]], [["⠳", "out"], ["⠳", "ou"]], [["⠌", "still"], ["⠌", "st"]]]
    for wordsign in wordsigns:
        wordsign_matches = re.finditer(wordsign[0][0], new_character_string)
        wordsign_match_indices = [match.start() for match in wordsign_matches]
        for i in range(len(wordsign_match_indices)-1, -1, -1):
            #If the braille character is found at the very start of the document, then only the
            #character after it needs to be checked to see whether it is a letter. If it is a
            #letter, then the groupsign is substituted for the braille character, as the wordsign
            #needs to stand alone.
            if (wordsign_match_indices[i] == 0 and
            new_character_string[wordsign_match_indices[i]+1] in (braille_alphabet + contraction_characters)):
                new_character_string = (new_character_string[:wordsign_match_indices[i]]
                + wordsign[1][1] + new_character_string[wordsign_match_indices[i]+1:])
            #If it is not a letter, the wordsign is substituted for the braille character, as the
            #groupsign would need to be flanked by a letter.
            elif (wordsign_match_indices[i] == 0 and
            new_character_string[wordsign_match_indices[i]+1] not in (braille_alphabet + contraction_characters)):
                new_character_string = (new_character_string[:wordsign_match_indices[i]]
                + wordsign[0][1] + new_character_string[wordsign_match_indices[i]+1:])
            #If the braille character is found at the very end of the document, then only the character
            #before it needs to be checked to see whether it is a letter. If it is a letter, then the
            #groupsign is substituted for the braille character, as the wordsign needs to stand alone.
            elif (wordsign_match_indices[i] == len(new_character_string) -1 and
            new_character_string[wordsign_match_indices[i]-1] in (braille_alphabet + contraction_characters)):
                new_character_string = (new_character_string[:wordsign_match_indices[i]]
                + wordsign[1][1] + new_character_string[wordsign_match_indices[i]+1:])
            #If the braille character is neither at the beginning nor end of the document, the characters
            #on either side of the braille character need to be checked to see whether they are a letter.
            #If at least one of them is a letter, then the groupsign is substituted for the braille character,
            #as the wordsign needs to stand alone.
            elif (wordsign_match_indices[i] == len(new_character_string) -1 and
            new_character_string[wordsign_match_indices[i]-1] not in (braille_alphabet + contraction_characters)):
                new_character_string = (new_character_string[:wordsign_match_indices[i]]
                + wordsign[0][1] + new_character_string[wordsign_match_indices[i]+1:])
            #If it is not a letter, the wordsign is substituted for the braille character, as the groupsign
            #would need to be flanked by at least one letter.
            elif (new_character_string[wordsign_match_indices[i]+1] in (braille_alphabet + contraction_characters) or
            new_character_string[wordsign_match_indices[i]-1] in (braille_alphabet + contraction_characters)):
                new_character_string = (new_character_string[:wordsign_match_indices[i]]
                + wordsign[1][1] + new_character_string[wordsign_match_indices[i]+1:])
            #Otherwise, the wordsign is substituted for the braille character.
            else:
                new_character_string = (new_character_string[:wordsign_match_indices[i]]
                + wordsign[0][1] + new_character_string[wordsign_match_indices[i]+1:])
    
    #Disambiguation for the "enough" wordsigns and its corresponding "en" groupsign.
    #If there is at least one letter on any side of the braille character, then the
    #substitution is done for the groupsign, as the wordsign must stand alone.
    #In addition to this, the "⠢" braille character must not be preceded by a
    #grade I symbol character "⠰", which when followed by "⠢" designates the
    #subscript indicator "⠰⠢".
    wordsigns = [["⠢", "enough"], ["⠢", "en"]]
    wordsign_matches = re.finditer(wordsigns[0][0], new_character_string)
    wordsign_match_indices = [match.start() for match in wordsign_matches]
    for i in range(len(wordsign_match_indices)-1, -1, -1):
        if (wordsign_match_indices[i] == 0 and
        new_character_string[wordsign_match_indices[i]+1] in (braille_alphabet + contraction_characters)):
            new_character_string = (new_character_string[:wordsign_match_indices[i]]
            + wordsigns[1][1] + new_character_string[wordsign_match_indices[i]+1:])
        elif (wordsign_match_indices[i] == 0
        and new_character_string[wordsign_match_indices[i]+1] not in (braille_alphabet + contraction_characters)):
            new_character_string = (new_character_string[:wordsign_match_indices[i]]
            + wordsigns[0][1] + new_character_string[wordsign_match_indices[i]+1:])
        #The "⠢" braille character must not be preceded by a grade I symbol character "⠰",
        #which when followed by "⠢" designates the subscript indicator "⠰⠢", so the
        #substitutions below only take place if the preceding character is not "⠰".
        elif wordsign_match_indices[i] > 0 and new_character_string[wordsign_match_indices[i]-1] != "⠰":
            if (wordsign_match_indices[i] == len(new_character_string) -1 and
            new_character_string[wordsign_match_indices[i]-1] in (braille_alphabet + contraction_characters)):
                new_character_string = (new_character_string[:wordsign_match_indices[i]]
                + wordsigns[1][1] + new_character_string[wordsign_match_indices[i]+1:])
            elif (wordsign_match_indices[i] == len(new_character_string) -1 and
            new_character_string[wordsign_match_indices[i]-1] not in (braille_alphabet + contraction_characters)):
                new_character_string = (new_character_string[:wordsign_match_indices[i]]
                + wordsigns[0][1] + new_character_string[wordsign_match_indices[i]+1:])
            elif (new_character_string[wordsign_match_indices[i]+1] in (braille_alphabet + contraction_characters) or
            new_character_string[wordsign_match_indices[i]-1] in (braille_alphabet + contraction_characters)):
                new_character_string = (new_character_string[:wordsign_match_indices[i]]
                + wordsigns[1][1] + new_character_string[wordsign_match_indices[i]+1:])
            else:
                new_character_string = (new_character_string[:wordsign_match_indices[i]]
                + wordsigns[0][1] + new_character_string[wordsign_match_indices[i]+1:])
    
    #The alphabetic wordsigns in "alphabetic_wordsigns" need stand alone for the substitution to
    #take place.
    alphabetic_wordsigns = [["⠺", "will"], ["⠝", "not"], ["⠟", "quite"], ["⠃", "but"],
    ["⠗", "rather"], ["⠽", "you"], ["⠉", "can"], ["⠓", "have"], ["⠍", "more"], ["⠅", "knowledge"],
    ["⠎", "so"], ["⠞", "that"], ["⠏", "people"], ["⠚", "just"], ["⠇", "like"], ["⠥", "us"],
    ["⠙", "do"], ["⠵", "as"], ["⠋", "from"], ["⠭", "it"], ["⠑", "every"], ["⠧", "very"], ["⠛", "go"]]
    for word in alphabetic_wordsigns:
        alphabetic_wordsign_matches = re.finditer(word[0], new_character_string)
        alphabetic_wordsign_match_indices = [match.start() for match in alphabetic_wordsign_matches]
        for i in range(len(alphabetic_wordsign_match_indices)-1, -1, -1):
            #If there is only one character after the match, then in order for the alphabetic
            #wordsign to stand alone, it must be one of the following: u"\u2800", "—", "—", "-",
            #"-", "_", "’", '”', '»', ")", "]", "}", "?", "!", ".",  "…", ",", ":", ";". If so,
            #The character(s) before it also need to be checked, as the only admissible characters
            #for a free-standing alphabetic wordsign would be an empty braille cell (u"\u2800"),
            #any typeform indicators for symbols, words or passages written in italics ("⠨⠆", "⠨⠂", "⠨⠶"),
            #bold ("⠘⠆", "⠘⠂", "⠘⠶"), underline ("⠸⠆", "⠸⠂", "⠸⠶") or script ("⠈⠆", "⠈⠂", "⠈⠶"), or
            #one of the following: "⠠", "—", "—", "-", "-", "_", "‘", '“', '«', "(", "[", "{". It is
            #assumed that a wordsign cannot be found as the very first character of a document, because
            #it would likely be preceded by a capitalization symbol ("⠠").
            if (alphabetic_wordsign_match_indices[i] == len(new_character_string) - 2 and
            new_character_string[alphabetic_wordsign_match_indices[i] + 1] in
            [u"\u2800", "—", "—", "-", "-", "_", "’", '”', '»', ")", "]", "}", "?", "!", ".",  "…", ",", ":", ";"]):
                if alphabetic_wordsign_match_indices[i] == 0:
                    new_character_string = word[1] + new_character_string[alphabetic_wordsign_match_indices[i] + 1:]
                elif (alphabetic_wordsign_match_indices[i] == 1 and
                new_character_string[alphabetic_wordsign_match_indices[i]-1] in
                [u"\u2800", "⠠", "—", "—", "-", "-", "_", "‘", '“', '«', "(", "[", "{"]):
                    new_character_string = (new_character_string[:alphabetic_wordsign_match_indices[i]]
                    + word[1] + new_character_string[alphabetic_wordsign_match_indices[i] + 1:])
                elif (alphabetic_wordsign_match_indices[i] >= 2 and
                (new_character_string[alphabetic_wordsign_match_indices[i]-2:alphabetic_wordsign_match_indices[i]] in
                ["⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶", "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶"] or
                new_character_string[alphabetic_wordsign_match_indices[i]-1] in
                [u"\u2800", "⠠", "—", "—", "-", "-", "_", "‘", '“', '«', "(", "[", "{"])):
                    new_character_string = (new_character_string[:alphabetic_wordsign_match_indices[i]]
                    + word[1] + new_character_string[alphabetic_wordsign_match_indices[i] + 1:])
            #If there are at least two characters after the match, then the typeform terminators for italics ("⠨⠄"),
            #bold ("⠘⠄"), underline ("⠸⠄") or script ("⠸⠄") need to be added to the admissible characters that could
            #follow an alphabetic wordsign, in addition to the ones mentioned above.
            elif (alphabetic_wordsign_match_indices[i] <= len(new_character_string) - 3 and
            (new_character_string[alphabetic_wordsign_match_indices[i] + 1:alphabetic_wordsign_match_indices[i] + 3] in
            [ "⠨⠄", "⠘⠄", "⠸⠄", "⠈⠄"] or
            new_character_string[alphabetic_wordsign_match_indices[i] + 1] in
            [u"\u2800", "—", "—", "-", "-", "_", "’", '”', '»', ")", "]", "}", "?", "!", ".",  "…", ",", ":", ";"])):
                if alphabetic_wordsign_match_indices[i] == 0:
                    new_character_string = word[1] + new_character_string[alphabetic_wordsign_match_indices[i] + 1:]
                elif (alphabetic_wordsign_match_indices[i] == 1 and
                new_character_string[alphabetic_wordsign_match_indices[i]-1] in
                [u"\u2800", "⠠", "—", "—", "-", "-", "_", "‘", '“', '«', "(", "[", "{"]):
                    new_character_string = (new_character_string[:alphabetic_wordsign_match_indices[i]]
                    + word[1] + new_character_string[alphabetic_wordsign_match_indices[i] + 1:])
                elif (alphabetic_wordsign_match_indices[i] >= 2 and
                (new_character_string[alphabetic_wordsign_match_indices[i]-2:alphabetic_wordsign_match_indices[i]] in
                ["⠨⠆", "⠨⠂", "⠨⠶", "⠘⠆", "⠘⠂", "⠘⠶", "⠸⠆", "⠸⠂", "⠸⠶", "⠈⠆", "⠈⠂", "⠈⠶"] or
                new_character_string[alphabetic_wordsign_match_indices[i]-1] in
                [u"\u2800", "⠠", "—", "—", "-", "-", "_", "‘", '“', '«', "(", "[", "{"])):
                    new_character_string = (new_character_string[:alphabetic_wordsign_match_indices[i]]
                    + word[1] + new_character_string[alphabetic_wordsign_match_indices[i] + 1:])
    
    #Disambiguation of "⠆": "be"
    #Since the "⠆" symbol matching the lower groupsign/wordsign "be" is also the second
    #character in all typeform symbol indicators, only the "⠆" matches that are not preceded
    #by the first character of the different typeform indicators will be transcribed to "be".
    be_matches = re.finditer("⠆", new_character_string)
    be_match_indices = [match.start() for match in be_matches]
    for i in range(len(be_match_indices)-1, -1, -1):
        #If "⠆" is the first character in the document, then it cannot be preceded by a
        #typeform indicator and can be transcribed to "be".
        if be_match_indices[i] == 0:
            new_character_string = (new_character_string[:be_match_indices[i]]
            + "be" + new_character_string[be_match_indices[i]+1:])
        elif be_match_indices[i] > 0 and new_character_string[be_match_indices[i]-1] not in ["⠨", "⠘", "⠸", "⠈"]:
            new_character_string = (new_character_string[:be_match_indices[i]]
            + "be" + new_character_string[be_match_indices[i]+1:])
    
    #The subscript indicator "⠰⠢" and superscript indicator "⠰⠔" are changed for their
    #RTF commands, with a curly bracket wrapped around the affected character. These
    #modifications are done after any algorithms requiring to check if a wordsign
    #stands alone, as the closing curly bracket would interfere with the results.
    indicators = [["⠰⠢", "{\sub⠀"], ["⠰⠔", "{\super⠀"]]
    for indicator in indicators:
        indicator_matches = re.finditer(indicator[0], new_character_string)
        indicator_match_indices = [match.start() for match in indicator_matches]
        for i in range(len(indicator_match_indices)-1, -1, -1):
            new_character_string = (new_character_string[:indicator_match_indices[i]] +
            indicator[1] + new_character_string[indicator_match_indices[i]+2] + "}" +
            new_character_string[indicator_match_indices[i]+3:])
    
    #Finally, the "in" groupsigns are substituted for the remaining "⠔" characters in the text,
    #once all possible other uses of the "⠔" braille character have been handled
    #("⠈⠔" mapping to the tilde "∼" and "⠐⠔" mapping to the asterisk "*")
    new_character_string = re.sub("⠔", "in", new_character_string)
    
    #Once all of the braille contractions are dealt with the remaining characters
    #would be changed to their printed English equivalents.
    braille_single_characters = {"⠁":"a", "⠃":"b", "⠉":"c", "⠙":"d", "⠑":"e",
    "⠋":"f", "⠛":"g", "⠓":"h", "⠊":"i", "⠚":"j", "⠅":"k", "⠇":"l", "⠍":"m",
    "⠝":"n", "⠕":"o", "⠏":"p", "⠟":"q", "⠗":"r", "⠎":"s", "⠞":"t", "⠥":"u",
    "⠧":"v", "⠺":"w", "⠭":"x", "⠽":"y", "⠵":"z",
    "⠯": "and", "⠿": "for", "⠷": "of", "⠮": "the", "⠾": "with", "⠣": "gh",
    "⠫": "ed", "⠻": "er", "⠪": "ow", "⠜": "ar", "⠬": "ing", "⠒": "con"}
    mapping_table = new_character_string.maketrans(braille_single_characters)
    new_character_string = new_character_string.translate(mapping_table)
    
    
    #The following sections deal with text formatting such as capitalization, italics,
    #bold, underline, script, superscript and subscript. These modifications need to be
    #performed after dealing with the contractions and ambiguities, since the code often checks
    #for the presence of letters before a given match, and the formatting inserts closing
    #Rich Text Formatting (RTF) commands that end with zero (such as "\b0"). If a contraction were to
    #be located right after a bold letter, for instance, the previous character
    #would no longer be a letter, but a digit or a space(ex: "⠠ ⠁⠒⠨⠞" or "account", would be converted
    #to "\b ⠁\b0 ⠒⠨⠞" or  \b⠁\b0⠒⠨⠞, depending on whether or not the optional space
    #is inserted after the RTF commands. In any case, the "⠒" character wouldn't have letters on
    #either side and would then be converted to ":".
    
    #The following section deals with capitalization/uppercase.
    #When the capitalization passage indicator "⠠⠠⠠" is encountered, capitalization
    #continues until the capitalization terminator symbol ("⠠⠄") is met.
    capitalization_passage_matches = re.finditer("⠠⠠⠠", new_character_string)
    capitalization_passage_match_indices = [match.start() for match in capitalization_passage_matches]
    for i in range(len(capitalization_passage_match_indices)-1, -1, -1):
        try:
            index_capitalization_terminator = (new_character_string
            .index("⠠⠄", capitalization_passage_match_indices[i]+3))
            passage_string = (r"\caps⠀" +
            new_character_string[capitalization_passage_match_indices[i]+3:index_capitalization_terminator] +
            r"\caps0⠀")
            new_character_string = (new_character_string[:capitalization_passage_match_indices[i]] +
            passage_string + new_character_string[index_capitalization_terminator+2:])
        #If the user forgot to put the termination symbols "⠠⠄" to close an capitalization passage
        #or if the OCR misassigned the braille characters within the termination symbols, these opening
        #capitalization symbols ("⠠⠠⠠") will be changed to an error message to guide the user in
        #proofreading their text.
        except:
            new_character_string = (new_character_string[:capitalization_passage_match_indices[i]] +
            "[Transcription note: a capitalization passage indicator was located here, but no capitalization terminator was found after it.] " +
            new_character_string[capitalization_passage_match_indices[i]+3:])
    
    #When the capitalization word indicator "⠠⠠" is encountered, capitalization continues
    #until one of the following are met: an empty braille cell (u"\u2800") or the capitalization
    #termination symbol ("⠠⠄"). As the different formatting terminators (u"\u2800", "⠠⠄") have
    #different lengths, it is important to register the length of the terminator, to skip over
    #the correct amount of characters ("terminator_length") when adding to the updated
    #"new_character_string" what comes after the terminator:
    #("new_character_string[index_capitalization_terminator+terminator_length:]").
    capitalization_word_matches = re.finditer("⠠⠠", new_character_string)
    capitalization_word_match_indices = [match.start() for match in capitalization_word_matches]
    for i in range(len(capitalization_word_match_indices)-1, -1, -1):
        word_starting_index = capitalization_word_match_indices[i]+2
        #The "terminator_found" variable is set to its default value of "False" and will
        #be changed to "True" when a character does not match one found in the
        #"braille_alphabet" list or if the character is either an empty braille cell (u"\u2800")
        #or the capitalization termination symbol ("⠠⠄"). The index of this character will
        #be stored in the "index_capitalization_terminator" variable and the "for j in..."
        #loop will be broken.
        terminator_found = False
        #If the match is the last one in the "capitalization_word_match_indices" list (the last
        #occurence of the formatting indicator in the document, but the first one processed in the
        #"for" loop):
        if i == len(capitalization_word_match_indices)-1:
            for j in range(capitalization_word_match_indices[i]+2, len(new_character_string)):
                #If the terminator is either a non alphabetic symbol or an empty braille cell ("u"\u2800""),
                #"terminator_length" is set to 0 in order to include the terminator symbol when updating the
                #"new_character_string".
                if (new_character_string[j] not in (braille_alphabet + contraction_characters) or
                new_character_string[j] == u"\u2800"):
                    index_capitalization_terminator = j
                    terminator_length = 0
                    capitalized_string = (
                    r"\caps⠀" +
                     new_character_string[capitalization_word_match_indices[i]+2:index_capitalization_terminator] +
                    r"\caps0⠀")
                    new_character_string = (new_character_string[:capitalization_word_match_indices[i]] +
                    capitalized_string + new_character_string[index_capitalization_terminator+terminator_length:])
                    terminator_found = True
                    break
                #If the terminator is the capitalization terminator symbols ("⠠⠄"), "terminator_length" is set to 2
                #in order to skip over the terminator symbols when updating the "new_character_string".
                elif (capitalization_word_match_indices[i] <= len(new_character_string)-3 and
                new_character_string[j:j+2] == "⠠⠄"):
                    index_capitalization_terminator = j
                    terminator_length = 2
                    capitalized_string = (
                    r"\caps⠀" +
                    new_character_string[capitalization_word_match_indices[i]+2:index_capitalization_terminator] +
                    r"\caps0⠀")
                    new_character_string = (new_character_string[:capitalization_word_match_indices[i]] +
                    capitalized_string + new_character_string[index_capitalization_terminator+terminator_length:])
                    terminator_found = True
                    break
    
        else:
            for k in range(capitalization_word_match_indices[i]+2, capitalization_word_match_indices[i+1]):
                #If the terminator is either a non alphabetic symbol or an empty braille cell ("u"\u2800""),
                #"terminator_length" is set to 0 in order to include the terminator symbol when updating the
                #"new_character_string".
                if (new_character_string[k] not in (braille_alphabet + contraction_characters) or
                new_character_string[k] == u"\u2800"):
                    index_capitalization_terminator = k
                    terminator_length = 0
                    capitalized_string = (
                    r"\caps⠀" +
                    new_character_string[capitalization_word_match_indices[i]+2:index_capitalization_terminator] +
                    r"\caps0⠀")
                    new_character_string = (new_character_string[:capitalization_word_match_indices[i]] +
                    capitalized_string + new_character_string[index_capitalization_terminator+terminator_length:])
                    terminator_found = True
                    break
                #If the terminator is the capitalization terminator symbols ("⠠⠄"), "terminator_length" is set to 2
                #in order to skip over the terminator symbols when updating the "new_character_string".
                elif (capitalization_word_match_indices[i] <= len(new_character_string)-3 and
                new_character_string[k:k+2] == "⠠⠄"):
                    index_capitalization_terminator = k
                    terminator_length = 2
                    capitalized_string = (
                    r"\caps⠀" +
                    new_character_string[capitalization_word_match_indices[i]+2:index_capitalization_terminator] +
                    r"\caps0⠀")
                    new_character_string = (new_character_string[:capitalization_word_match_indices[i]] +
                    capitalized_string + new_character_string[index_capitalization_terminator+terminator_length:])
                    terminator_found = True
                    break
    
            #In the event that only characters found in the list "braille_alphabet" were
            #encountered in the "for j(or k) in..." loop, then all the characters from the
            #"index new_character_string[capitalization_word_match_indices[i]+1"
            #(following the capitalization symbol) up to the index of the following
            #capitalization symbol must be capitalized. In the case of the first capitalized
            #match analyzed (which is actually the last occurence of the capitalization symbol
            #in the document) the capitalization occurs until the end of the document and
            #"new_character_string[index_capitalization_terminator:]" is not added after
            #the "capitalized_string".
            if terminator_found == False and i == len(capitalization_word_match_indices)-1:
                capitalized_string = (r"\caps⠀" +
                new_character_string[capitalization_word_match_indices[i]+2:] +
                r"\caps0⠀")
                new_character_string = (new_character_string[:capitalization_word_match_indices[i]] +
                capitalized_string)
            elif terminator_found == False and i != len(capitalization_word_match_indices)-1:
                index_capitalization_terminator = capitalization_word_match_indices[i+1]
                capitalized_string = (r"\caps⠀" +
                new_character_string[capitalization_word_match_indices[i]+2:index_capitalization_terminator] +
                r"\caps0⠀")
                new_character_string = (new_character_string[:capitalization_word_match_indices[i]] +
                capitalized_string + new_character_string[index_capitalization_terminator:])
    
    #When the capitalization symbol indicator "⠠" is encountered, capitalization is
    #applied only to the following letter. In this case, as capitalized letters begin
    #every sentence and are thus so common, the ".upper()" method is applied to the letter
    #instead of framing it with the RTF commands 'r"\caps"' and 'r"\caps0⠀"'. This
    #step is done once all of the indicators for capitalization passages ("⠠⠠⠠") and
    #words ("⠠⠠") have been dealt with.
    capitalization_symbol_matches = re.finditer("⠠", new_character_string)
    capitalization_symbol_match_indices = [match.start() for match in capitalization_symbol_matches]
    
    for i in range(len(capitalization_symbol_match_indices)-1, -1, -1):
        letter_after_capitalization_symbol = new_character_string[capitalization_symbol_match_indices[i]+1].upper()
        if capitalization_symbol_match_indices[i] == 0:
            new_character_string = (letter_after_capitalization_symbol +
            new_character_string[capitalization_symbol_match_indices[i]+2:])
        elif capitalization_symbol_match_indices[i] == len(new_character_string)-2:
            new_character_string = (new_character_string[:capitalization_symbol_match_indices[i]]
             + letter_after_capitalization_symbol)
        elif capitalization_symbol_match_indices[i] < len(new_character_string)-2:
            new_character_string = (new_character_string[:capitalization_symbol_match_indices[i]]
            + letter_after_capitalization_symbol + new_character_string[capitalization_symbol_match_indices[i] + 2:])
    
    
    #The following section deals with italics.
    #When the italics passage indicator "⠨⠶" is encountered, italics continues until the
    #italics terminator symbol ("⠨⠄") is met. When assembling the "new_character_string",
    #the text up to the italics match is added, skipping over the two italics passage
    #initiation symbols, the "passage_string" is then inserted, followed by the final
    #portion of the "new_character_string", starting at two characters after the
    #termination symbol (which is two characters in length, hence the
    #new_character_string[index_italics_terminator+2:])
    italics_passage_matches = re.finditer("⠨⠶", new_character_string)
    italics_passage_match_indices = [match.start() for match in italics_passage_matches]
    for i in range(len(italics_passage_match_indices)-1, -1, -1):
        try:
            index_italics_terminator = new_character_string.index("⠨⠄", italics_passage_match_indices[i]+2)
            passage_string = (r"\i " +
            new_character_string[italics_passage_match_indices[i]+2:index_italics_terminator] +
            r"\i0⠀")
            new_character_string = (new_character_string[:italics_passage_match_indices[i]] +
            passage_string + new_character_string[index_italics_terminator+2:])
        #If the user forgot to put the termination symbols "⠨⠄" to close an italics passage
        #or if the OCR misassigned the braille characters within the termination symbols,
        #these opening italics symbols ("⠨⠶") will be changed to an error message to guide
        #the user in proofreading their text.
        except:
            new_character_string = (new_character_string[:italics_passage_match_indices[i]] +
            "[Transcription note: an italics passage indicator was located here, but no italics terminator was found after it.] " +
            new_character_string[italics_passage_match_indices[i]+2:])
    
    
    #When the italics word indicator "⠨⠂" is encountered, italics continues until
    #one of the following are met: an empty braille cell (u"\u2800") or the italics
    #termination symbol ("⠨⠄"). As the different formatting terminators (u"\u2800", "⠨⠄")
    #have different lengths, it is important to register the length of the terminator,
    #to skip over the correct amount of characters ("terminator_length") when adding to
    #the updated "new_character_string" what comes after the terminator
    #("new_character_string[index_italics_terminator+terminator_length:]").
    italics_word_matches = re.finditer("⠨⠂", new_character_string)
    italics_word_match_indices = [match.start() for match in italics_word_matches]
    for i in range(len(italics_word_match_indices)-1, -1, -1):
        #The "terminator_found" variable is set to its default value of "False" and will
        #be changed to "True" when a character is either an empty braille cell (u"\u2800")
        #or the italics termination symbol ("⠨⠄"). The index of this character will be
        #stored in the "index_italics_terminator" variable and the "for j in..." loop will be broken.
        terminator_found = False
        #If the match is the last one in the "italics_word_match_indices" list (the last
        #occurrence of the formatting indicator in the document, but the first one processed in the
        #"for" loop):
        if i == len(italics_word_match_indices)-1:
            for j in range(italics_word_match_indices[i]+2, len(new_character_string)):
                if new_character_string[j] == u"\u2800":
                    index_italics_terminator = j
                    terminator_length = 0
                    italicized_string = (
                    r"\i⠀" +
                    new_character_string[italics_word_match_indices[i]+2:index_italics_terminator] +
                    r"\i0⠀")
                    new_character_string = (new_character_string[:italics_word_match_indices[i]] +
                    italicized_string + new_character_string[index_italics_terminator+terminator_length:])
                    terminator_found = True
                    break
    
                elif (italics_word_match_indices[i] <= len(new_character_string)-3 and
                new_character_string[j:j+2] == "⠨⠄"):
                    index_italics_terminator = j
                    terminator_length = 2
                    italicized_string = (
                    r"\i⠀" +
                    new_character_string[italics_word_match_indices[i]+2:index_italics_terminator] +
                    r"\i0⠀")
                    new_character_string = (new_character_string[:italics_word_match_indices[i]] +
                    italicized_string + new_character_string[index_italics_terminator+terminator_length:])
                    terminator_found = True
                    break
        else:
            for k in range(italics_word_match_indices[i]+2, italics_word_match_indices[i+1]):
                if new_character_string[k] == u"\u2800":
                    index_italics_terminator = k
                    terminator_length = 0
                    italicized_string = (
                    r"\i⠀" +
                    new_character_string[italics_word_match_indices[i]+2:index_italics_terminator] +
                    r"\i0⠀")
                    new_character_string = (new_character_string[:italics_word_match_indices[i]] +
                    italicized_string + new_character_string[index_italics_terminator+terminator_length:])
                    terminator_found = True
                    break
                elif (italics_word_match_indices[i] <= len(new_character_string)-3 and
                new_character_string[k:k+2] == "⠨⠄"):
                    index_italics_terminator = k
                    terminator_length = 2
                    italicized_string = (
                    r"\i⠀" +
                    new_character_string[italics_word_match_indices[i]+2:index_italics_terminator] +
                    r"\i0⠀")
                    new_character_string = (new_character_string[:italics_word_match_indices[i]] +
                    italicized_string + new_character_string[index_italics_terminator+terminator_length:])
                    terminator_found = True
                    break
        #In the event that no empty braille cells (u"\u2800") nor italics termination symbols ("⠨⠄")
        #were encountered in the "for j (or k) in..." loop, then all the characters from the index
        #"new_character_string[italics_word_match_indices[i]+2" (following the italics symbol) up to
        #the index of the following italics symbol must be italicized.
        #In the case of the first italicized match analyzed (which is actually the last occurence
        #of the italics symbol in the document) the italics occurs until the end of the document and
        #"new_character_string[index_italics_terminator:]" is not added after the "italicized_string".
        if terminator_found == False and i == len(italics_word_match_indices)-1:
            index_italics_terminator = len(new_character_string)-1
            italicized_string = r"\i⠀" + new_character_string[italics_word_match_indices[i]+2:] + r"\i0⠀"
            new_character_string = (new_character_string[:italics_word_match_indices[i]] +
            italicized_string)
        elif terminator_found == False and i != len(italics_word_match_indices)-1:
            index_italics_terminator = italics_word_match_indices[i+1]
            italicized_string = (r"\i⠀" +
            new_character_string[italics_word_match_indices[i]+2:index_italics_terminator] + r"\i0⠀")
            new_character_string = (new_character_string[:italics_word_match_indices[i]] +
            italicized_string + new_character_string[index_italics_terminator:])
    
    #When the italics symbol indicator "⠨⠆" is encountered, italics is applied only to the following letter.
    italics_symbol_matches = re.finditer("⠨⠆", new_character_string)
    italics_symbol_match_indices = [match.start() for match in italics_symbol_matches]
    
    for i in range(len(italics_symbol_match_indices)-1, -1, -1):
        letter_after_italics_symbol = r"{\i⠀" + new_character_string[italics_symbol_match_indices[i]+2] + "}"
        #If the "⠨⠆" match occurs before the last character in the document, that character is italicized
        #and added to the substring of "new_character_string" up to (but not including) the "⠨⠆".
        if italics_symbol_match_indices[i] == 0:
            new_character_string = (letter_after_italics_symbol +
            new_character_string[italics_symbol_match_indices[i]+2:])
        elif italics_symbol_match_indices[i] == len(new_character_string)-3:
            new_character_string = (new_character_string[:italics_symbol_match_indices[i]]
             + letter_after_italics_symbol)
        #If the "⠨⠆" match is located before the last character in the document, the rest of the
        #"new_character_string" after the italicized letter (3 indices away from the "⠨⠆" match)
        #will be added to the updated "new_character_string", after the italicized letter.
        elif italics_symbol_match_indices[i] < len(new_character_string)-3:
            new_character_string = (new_character_string[:italics_symbol_match_indices[i]]
            + letter_after_italics_symbol + new_character_string[italics_symbol_match_indices[i] + 3:])
    
    #The following section deals with bold.
    #When the bold passage indicator "⠘⠶" is encountered, bold continues until the
    #bold terminator symbol ("⠘⠄") is met. When assembling the "new_character_string",
    #the text up to the bold match is added, skipping over the two bold passage
    #initiation symbols, the "passage_string" is then inserted, followed by the final
    #portion of the "new_character_string", starting at two characters after the
    #termination symbol (which is two characters in length, hence the
    #new_character_string[index_bold_terminator+2:])
    bold_passage_matches = re.finditer("⠘⠶", new_character_string)
    bold_passage_match_indices = [match.start() for match in bold_passage_matches]
    for i in range(len(bold_passage_match_indices)-1, -1, -1):
        try:
            index_bold_terminator = new_character_string.index("⠘⠄", bold_passage_match_indices[i]+2)
            passage_string = (r"\b " +
            new_character_string[bold_passage_match_indices[i]+2:index_bold_terminator] + r"\b0⠀")
            new_character_string = (new_character_string[:bold_passage_match_indices[i]] +
            passage_string + new_character_string[index_bold_terminator+2:])
        #If the user forgot to put the termination symbols "⠘⠄" to close an bold passage or
        #if the OCR misassigned the braille characters within the termination symbols, these
        #opening bold symbols ("⠘⠶") will be changed to an error message to guide the user in
        #proofreading their text.
        except:
            new_character_string = (new_character_string[:bold_passage_match_indices[i]] +
            "[Transcription note: a bold passage indicator was located here, but no bold terminator was found after it.] " +
            new_character_string[bold_passage_match_indices[i]+2:])
    
    
    #When the bold word indicator "⠘⠂" is encountered, bold continues until one of the
    #following are met: an empty braille cell (u"\u2800") or the bold termination symbol ("⠘⠄").
    #As the different formatting terminators (u"\u2800", "⠘⠄") have different lengths, it is important
    #to register the length of the terminator, to skip over the correct amount of characters
    #("terminator_length") when adding to the updated "new_character_string" what comes after
    #the terminator ("new_character_string[index_bold_terminator+terminator_length:]").
    bold_word_matches = re.finditer("⠘⠂", new_character_string)
    bold_word_match_indices = [match.start() for match in bold_word_matches]
    for i in range(len(bold_word_match_indices)-1, -1, -1):
        #The "terminator_found" variable is set to its default value of "False" and will
        #be changed to "True" when a character is either an empty braille cell (u"\u2800")
        #or the bold termination symbol ("⠘⠄"). The index of this character will be
        #stored in the "index_bold_terminator" variable and the "for j in..." loop will be broken.
        terminator_found = False
        #If the match is the last one in the "bold_word_match_indices" list (the last
        #occurrence of the formatting indicator in the document, but the first one processed in the
        #"for" loop):
        if i == len(bold_word_match_indices)-1:
            for j in range(bold_word_match_indices[i]+2, len(new_character_string)):
                if new_character_string[j] == u"\u2800":
                    index_bold_terminator = j
                    terminator_length = 0
                    bold_string = (
                    r"\b⠀" +
                    new_character_string[bold_word_match_indices[i]+2:index_bold_terminator] +
                    r"\b0⠀")
                    new_character_string = (new_character_string[:bold_word_match_indices[i]] +
                    bold_string + new_character_string[index_bold_terminator+terminator_length:])
                    terminator_found = True
                    break
                elif (bold_word_match_indices[i] <= len(new_character_string)-3 and
                new_character_string[j:j+2] == "⠘⠄"):
                    index_bold_terminator = j
                    terminator_length = 2
                    bold_string = (
                    r"\b⠀" +
                    new_character_string[bold_word_match_indices[i]+2:index_bold_terminator] +
                    r"\b0⠀")
                    new_character_string = (new_character_string[:bold_word_match_indices[i]] +
                    bold_string + new_character_string[index_bold_terminator+terminator_length:])
                    terminator_found = True
                    break
        else:
            for k in range(bold_word_match_indices[i]+2, bold_word_match_indices[i+1]):
                if new_character_string[k] == u"\u2800":
                    index_bold_terminator = k
                    terminator_length = 0
                    bold_string = (
                    r"\b⠀" +
                    new_character_string[bold_word_match_indices[i]+2:index_bold_terminator] + r"\b0⠀")
                    new_character_string = (new_character_string[:bold_word_match_indices[i]] +
                    bold_string + new_character_string[index_bold_terminator+terminator_length:])
                    terminator_found = True
                    break
                elif (bold_word_match_indices[i] <= len(new_character_string)-3 and
                new_character_string[k:k+2] == "⠘⠄"):
                    index_bold_terminator = k
                    terminator_length = 2
                    bold_string = (
                    r"\b⠀" +
                    new_character_string[bold_word_match_indices[i]+2:index_bold_terminator] + r"\b0⠀")
                    new_character_string = (new_character_string[:bold_word_match_indices[i]] +
                    bold_string + new_character_string[index_bold_terminator+terminator_length:])
                    terminator_found = True
                    break
        #In the event that no empty braille cells (u"\u2800") nor bold termination symbols ("⠘⠄")
        #were encountered in the "for j (or k) in..." loop, then all the characters from the index
        #"new_character_string[bold_word_match_indices[i]+2" (following the bold symbol) up to
        #the index of the following bold symbol must be in bold format.
        #In the case of the first bold match analyzed (which is actually the last occurence
        #of the bold symbol in the document) the bold occurs until the end of the document and
        #"new_character_string[index_bold_terminator:]" is not added after the "bold_string".
        if terminator_found == False and i == len(bold_word_match_indices)-1:
            index_bold_terminator = len(new_character_string)-1
            bold_string = r"\b⠀" + new_character_string[bold_word_match_indices[i]+2:] + r"\b0⠀"
            new_character_string = (new_character_string[:bold_word_match_indices[i]] +
            bold_string)
        elif terminator_found == False and i != len(bold_word_match_indices)-1:
            index_bold_terminator = bold_word_match_indices[i+1]
            bold_string = (r"\b⠀" +
            new_character_string[bold_word_match_indices[i]+2:index_bold_terminator] + r"\b0⠀")
            new_character_string = (new_character_string[:bold_word_match_indices[i]] +
            bold_string + new_character_string[index_bold_terminator:])
    
    #When the bold symbol indicator "⠘⠆" is encountered, bold is applied only to the following letter.
    bold_symbol_matches = re.finditer("⠘⠆", new_character_string)
    bold_symbol_match_indices = [match.start() for match in bold_symbol_matches]
    
    for i in range(len(bold_symbol_match_indices)-1, -1, -1):
        letter_after_bold_symbol = r"{\b⠀" + new_character_string[bold_symbol_match_indices[i]+2] + "}"
        #If the "⠘⠆" match occurs before the last character in the document, that character is
        #converted to bold format and added to the substring of "new_character_string" up to
        #(but not including) the "⠘⠆".
        if bold_symbol_match_indices[i] == 0:
            new_character_string = (letter_after_bold_symbol +
            new_character_string[bold_symbol_match_indices[i]+2:])
        elif bold_symbol_match_indices[i] == len(new_character_string)-3:
            new_character_string = (new_character_string[:bold_symbol_match_indices[i]]
             + letter_after_bold_symbol)
        #If the "⠘⠆" match is located before the last character in the document, the rest of the
        #"new_character_string" after the bold letter (3 indices away from the "⠘⠆" match)
        #will be added to the updated "new_character_string", after the bold letter.
        elif bold_symbol_match_indices[i] < len(new_character_string)-3:
            new_character_string = (new_character_string[:bold_symbol_match_indices[i]]
            + letter_after_bold_symbol + new_character_string[bold_symbol_match_indices[i] + 3:])
    
    
    #The following section deals with underline.
    #When the underline passage indicator "⠸⠶" is encountered, underline continues until the
    #underline terminator symbol ("⠸⠄") is met. When assembling the "new_character_string",
    #the text up to the underline match is added, skipping over the two underline passage
    #initiation symbols, the "passage_string" is then inserted, followed by the final
    #portion of the "new_character_string", starting at two characters after the
    #termination symbol (which is two characters in length, hence the
    #new_character_string[index_underline_terminator+2:])
    underline_passage_matches = re.finditer("⠸⠶", new_character_string)
    underline_passage_match_indices = [match.start() for match in underline_passage_matches]
    for i in range(len(underline_passage_match_indices)-1, -1, -1):
        try:
            index_underline_terminator = new_character_string.index("⠸⠄", underline_passage_match_indices[i]+2)
            passage_string = (r"\ul " +
            new_character_string[underline_passage_match_indices[i]+2:index_underline_terminator] + r"\ul0⠀")
            new_character_string = (new_character_string[:underline_passage_match_indices[i]] +
            passage_string + new_character_string[index_underline_terminator+2:])
        #If the user forgot to put the termination symbols "⠸⠄" to close an underline passage
        #or if the OCR misassigned the braille characters within the termination symbols,
        #these opening underline symbols ("⠸⠶") will be changed to an error message to guide
        #the user in proofreading their text.
        except:
            new_character_string = (new_character_string[:underline_passage_match_indices[i]] +
            "[Transcription note: An underline passage indicator was located here, but no underline terminator was found after it.] " +
            new_character_string[underline_passage_match_indices[i]+2:])
    
    
    #When the underline word indicator "⠸⠂" is encountered, underline continues until one
    #of the following are met: an empty braille cell (u"\u2800") or the underline termination
    #symbol ("⠸⠄"). As the different formatting terminators (u"\u2800", "⠸⠄") have different
    #lengths, it is important to register the length of the terminator, to skip over the correct
    #amount of characters ("terminator_length") when adding to the updated "new_character_string"
    #what comes after the terminator ("new_character_string[index_underline_terminator+terminator_length:]").
    underline_word_matches = re.finditer("⠸⠂", new_character_string)
    underline_word_match_indices = [match.start() for match in underline_word_matches]
    for i in range(len(underline_word_match_indices)-1, -1, -1):
        #The "terminator_found" variable is set to its default value of "False" and will
        #be changed to "True" when a character is either an empty braille cell (u"\u2800")
        #or the underline termination symbol ("⠸⠄"). The index of this character will be
        #stored in the "index_underline_terminator" variable and the "for j in..." loop will be broken.
        terminator_found = False
        #If the match is the last one in the "underline_word_match_indices" list (the last
        #occurrence of the formatting indicator in the document, but the first one processed in the
        #"for" loop):
        if i == len(underline_word_match_indices)-1:
            for j in range(underline_word_match_indices[i]+2, len(new_character_string)):
                if new_character_string[j] == u"\u2800":
                    index_underline_terminator = j
                    terminator_length = 0
                    underline_string = (
                    r"\ul⠀" +
                    new_character_string[underline_word_match_indices[i]+2:index_underline_terminator] +
                    r"\ul0⠀")
                    new_character_string = (new_character_string[:underline_word_match_indices[i]] +
                    underline_string + new_character_string[index_underline_terminator+terminator_length:])
                    terminator_found = True
                    break
                elif (underline_word_match_indices[i] <= len(new_character_string)-3 and
                new_character_string[j:j+2] == "⠸⠄"):
                    index_underline_terminator = j
                    terminator_length = 2
                    underline_string = (
                    r"\ul⠀" +
                    new_character_string[underline_word_match_indices[i]+2:index_underline_terminator] +
                    r"\ul0⠀")
                    new_character_string = (new_character_string[:underline_word_match_indices[i]] +
                    underline_string + new_character_string[index_underline_terminator+terminator_length:])
                    terminator_found = True
                    break
        else:
            for k in range(underline_word_match_indices[i]+2, underline_word_match_indices[i+1]):
                if new_character_string[k] == u"\u2800":
                    index_underline_terminator = k
                    terminator_length = 0
                    underline_string = (
                    r"\ul⠀" +
                    new_character_string[underline_word_match_indices[i]+2:index_underline_terminator] +
                    r"\ul0⠀")
                    new_character_string = (new_character_string[:underline_word_match_indices[i]] +
                    underline_string + new_character_string[index_underline_terminator+terminator_length:])
                    terminator_found = True
                    break
                elif (underline_word_match_indices[i] <= len(new_character_string)-3 and
                new_character_string[k:k+2] == "⠸⠄"):
                    index_underline_terminator = k
                    terminator_length = 2
                    underline_string = (
                    r"\ul⠀" +
                    new_character_string[underline_word_match_indices[i]+2:index_underline_terminator] +
                    r"\ul0⠀")
                    new_character_string = (new_character_string[:underline_word_match_indices[i]] +
                    underline_string + new_character_string[index_underline_terminator+terminator_length:])
                    terminator_found = True
                    break
        #In the event that no empty braille cells (u"\u2800") nor underline termination symbols ("⠸⠄")
        #were encountered in the "for j (or k) in..." loop, then all the characters from the index
        #"new_character_string[underline_word_match_indices[i]+2" (following the underline symbol) up to
        #the index of the following underline symbol must be underlined.
        #In the case of the first underline match analyzed (which is actually the last occurence
        #of the underline symbol in the document) the underline occurs until the end of the document and
        #"new_character_string[index_underline_terminator:]" is not added after the "underline_string".
        if terminator_found == False and i == len(underline_word_match_indices)-1:
            index_underline_terminator = len(new_character_string)-1
            underline_string = r"\ul⠀" + new_character_string[underline_word_match_indices[i]+2:] + r"\ul0⠀"
            new_character_string = (new_character_string[:underline_word_match_indices[i]] +
            underline_string)
        elif terminator_found == False and i != len(underline_word_match_indices)-1:
            index_underline_terminator = underline_word_match_indices[i+1]
            underline_string = (r"\ul⠀" +
            new_character_string[underline_word_match_indices[i]+2:index_underline_terminator] + r"\ul0⠀")
            new_character_string = (new_character_string[:underline_word_match_indices[i]] +
            underline_string + new_character_string[index_underline_terminator:])
    
    #When the underline symbol indicator "⠸⠆" is encountered, underline is applied only to the following letter.
    underline_symbol_matches = re.finditer("⠸⠆", new_character_string)
    underline_symbol_match_indices = [match.start() for match in underline_symbol_matches]
    
    for i in range(len(underline_symbol_match_indices)-1, -1, -1):
        letter_after_underline_symbol = r"{\ul⠀" + new_character_string[underline_symbol_match_indices[i]+2] + "}"
        #If the "⠸⠆" match occurs before the last character in the document, that character is underlined and added
        #to the substring of "new_character_string" up to (but not including) the "⠸⠆".
        if underline_symbol_match_indices[i] == 0:
            new_character_string = (letter_after_underline_symbol +
            new_character_string[underline_symbol_match_indices[i]+2:])
        elif underline_symbol_match_indices[i] == len(new_character_string)-3:
            new_character_string = (new_character_string[:underline_symbol_match_indices[i]]
             + letter_after_underline_symbol)
        #If the "⠸⠆" match is located before the last character in the document, the rest of the
        #"new_character_string" after the underline letter (3 indices away from the "⠸⠆" match)
        #will be added to the updated "new_character_string", after the underline letter.
        elif underline_symbol_match_indices[i] < len(new_character_string)-3:
            new_character_string = (new_character_string[:underline_symbol_match_indices[i]]
            + letter_after_underline_symbol + new_character_string[underline_symbol_match_indices[i] + 3:])
    
    
    #The following section deals with script (which maps to the rtf command "\fs56" that
    #increases the font size to 56 points. This could be useful for titles and the user
    #could customize the default font settings associated with the script typeform).
    #When the script passage indicator "⠈⠶" is encountered, script continues until the
    #script terminator symbol ("⠈⠄") is met. When assembling the "new_character_string",
    #the text up to the script match is added, skipping over the two script passage
    #initiation symbols, the "passage_string" is then inserted, followed by the final
    #portion of the "new_character_string", starting at two characters after the
    #termination symbol (which is two characters in length, hence the
    #new_character_string[index_script_terminator+2:])
    script_passage_matches = re.finditer("⠈⠶", new_character_string)
    script_passage_match_indices = [match.start() for match in script_passage_matches]
    for i in range(len(script_passage_match_indices)-1, -1, -1):
        try:
            index_script_terminator = new_character_string.index("⠈⠄", script_passage_match_indices[i]+2)
            passage_string = (r"{\fs56 " +
            new_character_string[script_passage_match_indices[i]+2:index_script_terminator] + "}")
            new_character_string = (new_character_string[:script_passage_match_indices[i]] +
            passage_string + new_character_string[index_script_terminator+2:])
        #If the user forgot to put the termination symbols "⠈⠄" to close an script passage
        #or if the OCR misassigned the braille characters within the termination symbols,
        #these opening script symbols ("⠈⠶") will be changed to an error message to guide
        #the user in proofreading their text.
        except:
            new_character_string = (new_character_string[:script_passage_match_indices[i]] +
            "[Transcription note: a script passage indicator was located here, but no script terminator was found after it.] " +
            new_character_string[script_passage_match_indices[i]+2:])
    
    #When the script word indicator "⠈⠂" is encountered, script continues until one of
    #the following are met: an empty braille cell (u"\u2800") or the script termination
    #symbol ("⠈⠄"). As the different formatting terminators (u"\u2800", "⠈⠄") have different
    #lengths, it is important to register the length of the terminator, to skip over the
    #correct amount of characters ("terminator_length") when adding to the updated
    #"new_character_string" what comes after the terminator
    #("new_character_string[index_script_terminator+terminator_length:]").
    script_word_matches = re.finditer("⠈⠂", new_character_string)
    script_word_match_indices = [match.start() for match in script_word_matches]
    for i in range(len(script_word_match_indices)-1, -1, -1):
        #The "terminator_found" variable is set to its default value of "False" and will
        #be changed to "True" when a character is either an empty braille cell (u"\u2800")
        #or the script termination symbol ("⠈⠄"). The index of this character will be
        #stored in the "index_script_terminator" variable and the "for j in..." loop will be broken.
        terminator_found = False
        #If the match is the last one in the "script_word_match_indices" list (the last
        #occurrence of the formatting indicator in the document, but the first one processed in the
        #"for" loop):
        if i == len(script_word_match_indices)-1:
            for j in range(script_word_match_indices[i]+2, len(new_character_string)):
                if new_character_string[j] == u"\u2800":
                    index_script_terminator = j
                    terminator_length = 0
                    script_string = (
                    r"{\fs56⠀" +
                    new_character_string[script_word_match_indices[i]+2:index_script_terminator] + "}")
                    new_character_string = (new_character_string[:script_word_match_indices[i]] +
                    script_string + new_character_string[index_script_terminator+terminator_length:])
                    terminator_found = True
                    break
                elif (script_word_match_indices[i] <= len(new_character_string)-3 and
                new_character_string[j:j+2] == "⠈⠄"):
                    index_script_terminator = j
                    terminator_length = 2
                    script_string = (
                    r"{\fs56⠀" +
                    new_character_string[script_word_match_indices[i]+2:index_script_terminator] + "}")
                    new_character_string = (new_character_string[:script_word_match_indices[i]] +
                    script_string + new_character_string[index_script_terminator+terminator_length:])
                    terminator_found = True
                    break
        else:
            for k in range(script_word_match_indices[i]+2, script_word_match_indices[i+1]):
                if new_character_string[k] == u"\u2800":
                    index_script_terminator = k
                    terminator_length = 0
                    script_string = (
                    r"{\fs56⠀" +
                    new_character_string[script_word_match_indices[i]+2:index_script_terminator] + "}")
                    new_character_string = (new_character_string[:script_word_match_indices[i]] +
                    script_string + new_character_string[index_script_terminator+terminator_length:])
                    terminator_found = True
                    break
                elif (script_word_match_indices[i] <= len(new_character_string)-3 and
                new_character_string[k:k+2] == "⠈⠄"):
                    index_script_terminator = k
                    terminator_length = 2
                    script_string = (
                    r"{\fs56⠀" +
                    new_character_string[script_word_match_indices[i]+2:index_script_terminator] + "}")
                    new_character_string = (new_character_string[:script_word_match_indices[i]] +
                    script_string + new_character_string[index_script_terminator+terminator_length:])
                    terminator_found = True
                    break
        #In the event that no empty braille cells (u"\u2800") nor script termination symbols ("⠈⠄")
        #were encountered in the "for j (or k) in..." loop, then all the characters from the index
        #"new_character_string[script_word_match_indices[i]+2" (following the script symbol) up to
        #the index of the following script symbol must be in script format.
        #In the case of the first script match analyzed (which is actually the last occurence
        #of the script symbol in the document) the script occurs until the end of the document and
        #"new_character_string[index_script_terminator:]" is not added after the "script_string".
        if terminator_found == False and i == len(script_word_match_indices)-1:
            index_script_terminator = len(new_character_string)-1
            script_string = r"{\fs56⠀" + new_character_string[script_word_match_indices[i]+2:] + "}"
            new_character_string = (new_character_string[:script_word_match_indices[i]] +
            script_string)
        elif terminator_found == False and i != len(script_word_match_indices)-1:
            index_script_terminator = script_word_match_indices[i+1]
            script_string = (r"{\fs56⠀" +
            new_character_string[script_word_match_indices[i]+2:index_script_terminator] + "}")
            new_character_string = (new_character_string[:script_word_match_indices[i]] +
            script_string + new_character_string[index_script_terminator:])
    
    #When the script symbol indicator "⠈⠆" is encountered, script is applied only to the following letter.
    script_symbol_matches = re.finditer("⠈⠆", new_character_string)
    script_symbol_match_indices = [match.start() for match in script_symbol_matches]
    
    for i in range(len(script_symbol_match_indices)-1, -1, -1):
        letter_after_script_symbol = r"{\fs56⠀" + new_character_string[script_symbol_match_indices[i]+2] + "}"
        #If the "⠈⠆" match occurs before the last character in the document, that character is converted
        #to script format and added to the substring of "new_character_string" up to (but not including) the "⠈⠆".
        if script_symbol_match_indices[i] == 0:
            new_character_string = letter_after_script_symbol + new_character_string[script_symbol_match_indices[i]+2:]
        elif script_symbol_match_indices[i] == len(new_character_string)-3:
            new_character_string = (new_character_string[:script_symbol_match_indices[i]]
             + letter_after_script_symbol)
        #If the "⠈⠆" match is located before the last character in the document, the rest of the
        #"new_character_string" after the script letter (3 indices away from the "⠈⠆" match)
        #will be added to the updated "new_character_string", after the script letter.
        elif script_symbol_match_indices[i] < len(new_character_string)-3:
            new_character_string = (new_character_string[:script_symbol_match_indices[i]]
            + letter_after_script_symbol + new_character_string[script_symbol_match_indices[i] + 3:])
    
    
    #The following characters were substituted for their braille equivalents in order
    #to simplify the code (looking for one character instead of a combination of characters
    #constituting an RTF escape). Now that braille transcription is complete, they must
    #be changed to their respective RTF escapes in order to display properly in the RTF
    #document.
    rtf_escapes = [["’", r"\'92"], ["-", r"\'2d"], ['-', r"\'2d"], ['“', r"\'93"],
    ['”', r"\'94"], ["‘", r"\'91"], ["—", r"\'97"], ['—', r"\'96"],
    ['…', r"\'85"], ['_', r"\'5f"], ['«', r"\'ab"], ['»', r"\'bb"]]
    for escape in rtf_escapes:
        new_character_string = re.sub(escape[0], escape[1], new_character_string)
    
    #Empty braille cells (if present) are then removed before closing parentheses,
    #question marks, exclamation marks, commas, colons, semicolons and RTF escapes
    #for closing double (\'94) or single (\'92) quotes, as there should typically
    #not be any spaces before these characters.
    (new_character_string.replace("⠀)", ")").replace("⠀?", "?").replace("⠀!", "!")
    .replace("⠀,", ",").replace("⠀:", ":").replace("⠀;", ";").replace("⠀\\'94", "\\'94")
    .replace("⠀\\'92", "\\'92"))
    
    #The empty braille cells are then changed for spaces, and the string is stripped
    #to remove the space at the very end of the document.  An empty braille cell
    #had been added at the end of the OCR document because some of the transcription
    #Python code looks at the character following a match in order to decide on the
    #transcription outcome, and it wouldn't make sense to add specific "else" statements
    #to account for all these case scenarios, as the words wouldn't normally be found at the very
    #end of the document in the first place, but would rather be followed by a punctuation mark.
    #Finally, the RTF command "\par " is changed to "\par \tab", as tabs are typically used
    #when starting a new paragraph. Here I don't need to include the space which should have
    #been written after "\par", as the same space will be found after  "\tab".
    new_character_string = re.sub("⠀", " ", new_character_string).strip().replace(r"\par", r"\par \tab")
    

    # Replace empty braille cells with spaces and strip trailing whitespace.
    # Also convert \par to \par \tab (standard paragraph indentation).
    new_character_string = re.sub("\u2800", " ", new_character_string).strip()
    new_character_string = new_character_string.replace(r"\par", r"\par \tab")
    return new_character_string
