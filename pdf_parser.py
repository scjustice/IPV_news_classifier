#!/usr/bin/python3
import pdftotext
import numpy as np
import pandas as pd
import re
import sys

pdf_path = "./census-domestic-violence-gun-homicides-arizona.pdf"
output_csv = './census-domestic-violence-arizona.csv'

# To Do:
# Add runline parameters to set input pdf and output csv
# Add capability to adjust hard codes like make characters between columns

bDEBUG = False

def test_format(x, count, page):
    '''
    When testing, print the line in a format so that it's possible to tell
    which part of the pdf the is being parsed.
    '''

    if bDEBUG:
        return '(Page:{} Line:{}){}'.format(page, count, x)
    else:
        return '{}'.format(x)

def handle_special_lines(col_list, line_length):
    ''' 
    Because of the way that the pdf is formatted with the data split between
    three columns, there are many instances where the text for the columns do
    not line up. This helper function returns a list of three elements with 
    strings for each column or empty strings when there was no string for 
    that column. This also handles hidden columns where there is only a single
    space between the end of a column and the start of the next column.
    '''
    # print(split_list)
    # Line is already divided into three sections so return that list
    if len(col_list) == 3:
        # print('Line already split')
        return col_list

    # Check for hidden columns
    for cur_index, cur_col in enumerate(col_list):
        # print(cur_index)
        # print(cur_col)
        # If the currrent column has more than 42 characters then check for a 
        # hidden column.
        hidden_test = False
        if len(cur_col) > 42:
            hidden_test, new_cols = check_for_hidden_split(cur_col)
            #hidden_test, *new_cols = check_for_hidden_split(cur_col)
        if hidden_test:
            if cur_index == 0:
                new_list = new_cols
                if len(col_list) == 2:
                    new_list.append(col_list[1])
                    # print(new_list)
                elif len(new_cols) == 3:
                    # Handle when first, second, and third columns were combined
                    new_list = new_cols
                else:
                    new_list.append('')
            else:
                new_list = [col_list[0]] + new_cols
            return new_list
    # Handle column one only
    if len(col_list) == 1:
        return col_list + ['','']
    # Handle column two only
    elif len(col_list) == 2:
        if line_length < 96:
            return col_list + ['']
        else:
            return [col_list[0], '', col_list[1]]
    
    
def check_for_hidden_split(cur_col):
    '''
    Check for combined first, second, and third columns using heuristics
    based on the typical length of each column
    '''
    # First check for potentially combined first, second, and third columns.
    if len(cur_col) > 92:
        test_substring1 = cur_col[42:92]
        test_substring2 = cur_col[92:]
        if len(test_substring2) > 5:
            next_space1 = cur_col.find(' ', 42)
            next_space2 = cur_col.find(' ', 92)
            return(True, list((cur_col[:next_space1], cur_col[next_space1+1:next_space2], cur_col[next_space2+1:])))
    # Check for combined first and second or second and third columns
    else:
        # print('Current split is longer than 42')
        # Find the next space in the string after the 42nd character
        next_space = cur_col.find(' ',42)
        # print('next_space = {}'.format(next_space))
        test_substring = cur_col[42:]
        # If the length of the substring to see if there is a hidden column.
        if len(test_substring) < 5:
            # If the substring is less than 5 characters then there isn't a hidden
            # column
            return (False, cur_col)
        else:
            # print('Splitting columns')
            # If the substring is larger then 5 characters then split the line
            # at the next space after the 42 character.
            return (True, list((cur_col[:next_space], cur_col[next_space+1:])))

def parsePDFText(pdf_path, start_page, end_page):
    '''
    Main function to read in the contents of the pdf between the start 
    and the end page 
    '''
    # print('In parsePDFText')
    total_parse = ''
    with open(pdf_path, "rb") as f:
        pdf = pdftotext.PDF(f)

    for inst in range(start_page, end_page+1):
        # One column for each column in the pdf.
        col1 = []
        col2 = []
        col3 = []
        cur_page = ''
        # print('Parsing page {}'.format(inst))
        count = 0
        for cur_line in pdf[inst].splitlines():
            # some lines begin with a space so remove the single space 
            if cur_line[0] == ' ':
                cur_line = cur_line[1:]
            # skip lines that contain the page numbers
            if re.search('(?:PAGE|P A G E) \d+', cur_line):
                count += 1
                continue
            # Substitue multiple spaces with the | character and split on |
            test_line = re.sub('\s\s{1,52}', '|', cur_line)
            test_cols = test_line.split('|')
            # Don't parse the first few lines since they contain the title
            if (inst == start_page and count < 4):
                # Add the title to the first column
                col1.append(cur_line)
                count += 1
                continue

            # Test if the columns are split correctly, and handle appropriately
            cur_cols = handle_special_lines(test_cols, len(cur_line))
            # print(cur_split)
            
            # Append each column to the correct column
            col1.append(cur_cols[0])
            col2.append(cur_cols[1])
            col3.append(cur_cols[2])

            # count number of lines for title
            count += 1
        # Remove the the empty strings from the column lists
        col1 = [x for x in col1 if x != '']
        col2 = [x for x in col2 if x != '']
        col3 = [x for x in col3 if x != '']

        # Combine each column together to get the data on each page and then
        # add the page to the strings from the other pages.
        cur_page = ' '.join(col1 + col2 + col3)
        total_parse += ' ' + cur_page
        if bDEBUG:
            print(total_parse)
    return total_parse


# print(total_parse)


def split_paragraphs(text):
    # Split the text in to individual paragraphs.
    # Paragraphs begin with a string like PHOENIX, DECEMBER 11, 2013
    paragraph_string = re.sub(r'([A-Z ]+,? (?:AZ, |- )?[A-Z]+,? \d+, \d+ )', r'\n\1', text)
    paragraph_list = paragraph_string.splitlines()
    return paragraph_list


def parse_paragraph(cur_para):
    '''
    Parse each paragraph to have the location, date, text, and subcategories
    for each entry
    '''
    # print('In parse_paragraph')
    # print(cur_para)
    if (bDEBUG):
        return {}
    # Check if the paragraph contains the location 
    # If not then just add the paragraph to the return dictionary 
    # as text and return
    match = re.search(r'^([A-Z ]+),? (?:AZ, |- )?([A-Z]+,? \d+, \d+) ?', cur_para)
    ret_dict = {}
    if match is None:
        ret_dict['Text'] = [cur_para]
        return ret_dict
    Location = match.group(1).strip()
    Date = match.group(2).strip()
    case_text = re.sub(r'^([A-Z ]+,? (?:AZ, |- )?[A-Z]+,? \d+, \d+ )', '', cur_para)
    # case_text = re.sub(r'([A-Z ]+ ?[,-] [A-Z]+ \d+, \d+ )', '', cur_para)
    test_for_shooter_info = case_text.find('Shooter Suicide:')
    ret_dict = {'Location': [Location], 'Date': [Date], 'Text': [case_text]}
    # Check if the pdf contains the Shooter Suicide and other classifications
    if test_for_shooter_info >= 0:
        # Separate out the shooter info from the text entry
        shooter_info = case_text[test_for_shooter_info:]
        case_text = case_text[:test_for_shooter_info]
        ret_dict['Text'] = [case_text.rstrip()]
        
        # Handle that the shooter categories have multiple entries at times
        shooter_columns = ['Shooter Suicide',
                           'Shooter DV History|Shooter Domestic ' +
                           'Violence History',
                           'Shooter Had Prior Convictions|Had Prior ' +
                           'Convictions',
                           'Order of Protection',
                           'Order Required Shooter to Turn in Firearms',
                           'Fed. Prohib. from Owning Firearms|Fed ' +
                           'Prohibited / Owning Firearms']
        for cur_col in shooter_columns[1:]:
            if re.search(cur_col, shooter_info):
                # print('Found column: {}'.format(cur_col))
                # Unify the string for each classification
                shooter_info = re.sub(cur_col,
                                      '\n'+cur_col.split('|')[0],
                                      shooter_info)
        # ret_dict['Shooter Info'] = shooter_info
        temp_dict = {'Shooter Suicide': '', 'Shooter DV History': '',
                     'Had Prior Convictions': '', 'Order of Protection': '',
                     'Order Required Shooter to Turn in Firearms': '',
                     'Fed. Prohib. from Owning Firearms': ''}

        # print(shooter_info)
        for cur_col in temp_dict.keys():
            # Search for each key and use regex to parse out the values
            if re.search(cur_col, shooter_info):
                if cur_col.count('|') == 1:
                    cur_col = cur_col.split('|')[0]
                # print('regex is "({}): (.*?) ?\n"'.format(cur_col))
                match = re.search(r'({}): (.*?) ?(?:\n|$)'.format(cur_col),
                                  shooter_info)
                if match:
                    # print('Found col is {}'.format(match.group(1)))
                    # print('Variable is {}'.format(match.group(2)))
                    temp_dict[cur_col] = match.group(2)
            else:
                temp_dict[cur_col] = 'N/A'
        # Save shooter information to a dictionary for dataframe creation
        ret_dict['shooter_suicide'] = [temp_dict['Shooter Suicide']]
        ret_dict['dv_history'] = [temp_dict['Shooter DV History']]
        ret_dict['prior_convict'] = [temp_dict['Had Prior Convictions']]
        ret_dict['order_of_protect'] = [temp_dict['Order of Protection']]
        ret_dict['require_turn_in_firearm'] = [temp_dict['Order Required ' +
                                                         'Shooter to Turn ' +
                                                         'in Firearms']]
        ret_dict['fed_prohib'] = temp_dict['Fed. Prohib. from Owning Firearms']
    return ret_dict


total_parse = parsePDFText(pdf_path, 20, 32)
# test_para_list = split_paragraphs(total_parse)
# print(parse_paragraph(test_para_list[1]))
para_df = pd.DataFrame()
for cur_para in split_paragraphs(total_parse):
    # print(cur_para)
    # Create a dictionary for each paragraph and save that in a dataframe
    cur_dict = parse_paragraph(cur_para)
    # print(cur_dict)
    # print(pd.DataFrame.from_dict(cur_dict))
    para_df = para_df.append(pd.DataFrame(cur_dict), ignore_index=True,
                             sort=False)

# print(para_df)
if not bDEBUG:
    # Write the dataframe containing the information for each entry in the pdf
    para_df.to_csv(output_csv, index=False)
