import argparse, os, glob, json
import numpy as np
import pandas as pd
import re

'''
Call parser with: [python lookml_parser.py -wd 'LookML repository']
Generates:
1. List of views and first-degree sources
2. List of explores and first-degree sources (views)
3. List of explore-derived views
4. Model includes for .view.lkml and .model.lkml files
5. JSON representation of models
6. D3.js tree renderings of models
'''

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-wd', '--working-directory', help='LookML directory', dest='wd', required=True)
    args = parser.parse_args()
    return args

def return_ml(view):
    with open(view, 'r') as f:
        ml = f.read()
    return ml

def parse_files(wd):
    os.chdir(wd)

    model_files = []
    view_files = []
    docs = []

    for file in glob.glob('*.model.lkml'):
        model_files.append(file)

    for file in glob.glob('*.view.lkml'):
        view_files.append(file)

    for file in glob.glob('*.md'):
        docs.append(file)

    return model_files, view_files, docs

def get_explores(model_file, file_type, ml):
    explores_info = []

    explores_raw = re.findall(r"explore:([a-zA-Z0-9_\s]+){", ml)
    explores = []
    for explore_raw in explores_raw:
        explores.append(explore_raw.strip())

    num_explores = len(explores)

    '''
    explores can be sourced in three ways:
    1. from:
    2. join:
    3. always_join:
    4. if no view(s) are specified, the source is a view with the same name as the explore itself
    '''

    if num_explores > 1:
        for explore in explores:
            explore_info = {}
            explore_info['explore_name'] = explore
            explore_info['explore_file_location'] = model_file

            explore_sequence = explores.index(explore)
            explore_start_char = ml.find('explore: ' + explore)
            if explore_sequence + 1 < num_explores:
                explore_end_char = ml.find('explore: ' + explores[explore_sequence + 1])
            else:
                explore_end_char = len(ml)

            explore_ml = ml[explore_start_char:explore_end_char]

            source_from = re.findall(r"from:([a-zA-Z0-9._\s]*\n)",explore_ml)
            source_join = re.findall(r"join:([a-zA-Z0-9._\s]*){", explore_ml)
            source_always_join = re.findall(r"always_join:([\[\]a-zA-Z0-9._\s]*\n)",explore_ml)

            view_sources = []

            if source_from:
                for item in source_from:
                    view_sources.append(item.replace('\n', '').strip())

            if source_join:
                for item in source_join:
                    view_sources.append(item.replace('\n', '').strip())

            if source_always_join:
                for item in source_always_join:
                    view_sources.append(((item.replace('\n', '')).replace('[', '')).replace(']', '').strip())

            unique_view_sources = list(set(view_sources))
            if len(unique_view_sources) == 0:
                unique_view_sources.append(explore)
            explore_info['view_sources'] = unique_view_sources
            explore_info['syntax_error'] = None

            if file_type != 'model':
                explore_info['syntax_error'] = 'flagged explore as created in view file'
            explores_info.append(explore_info)

    elif num_explores == 1:
        explore_info = {}
        explore = explores[0]
        explore_info['explore_name'] = explore
        explore_info['explore_file_location'] = model_file

        explore_ml = ml

        source_from = re.findall(r"from:([a-zA-Z0-9._\s]*\n)", explore_ml)
        source_join = re.findall(r"join:([a-zA-Z0-9._\s]*){", explore_ml)
        source_always_join = re.findall(r"always_join:([\[\]a-zA-Z0-9._\s]*\n)", explore_ml)

        view_sources = []

        if source_from:
            for item in source_from:
                view_sources.append(item.replace('\n', '').strip())

        if source_join:
            for item in source_join:
                view_sources.append(item.replace('\n', '').strip())

        if source_always_join:
            for item in source_always_join:
                view_sources.append(((item.replace('\n', '')).replace('[', '')).replace(']', '').strip())

        unique_view_sources = list(set(view_sources))
        if len(unique_view_sources) == 0:
            unique_view_sources.append(explore)
        explore_info['view_sources'] = unique_view_sources
        explore_info['syntax_error'] = None
        if file_type != 'model':
            explore_info['syntax_error'] = 'flagged explore as created in view file'
        explores_info.append(explore_info)

    return explores_info

def get_views(view_file, file_type, ml):
    """
    once all view files have been processed, extract all view names and dependencies 
    """
    views_info = []

    views_raw = re.findall(r"view:([a-zA-Z0-9_\s]+){", ml)
    views = []
    for view_raw in views_raw:
        views.append(view_raw.strip())

    num_views = len(views)

    """
    there are three types of views:
    1. sql tables (sql_table_name: [X])
    2. derived tables from explores (derived_table: { explore_source: [X] {)
    3. derived tables from sql (derived_table: { sql: )
    """

    if num_views > 1:
        for view in views:
            view_info = {}
            view_info['view_name'] = view
            view_info['view_file_location'] = view_file

            view_sequence = views.index(view)
            view_start_char = ml.find(view)
            if view_sequence + 1 < num_views:
                view_end_char = ml.find(views[view_sequence + 1], view_start_char + 50)
            else:
                view_end_char = len(ml)

            view_ml = ml[view_start_char:view_end_char]

            derived_table_explore = re.findall(r"derived_table:([\s\n]*){([\s\n]*)explore_source:([a-zA-Z0-9_\s\n]*){", view_ml)
            derived_table_sql = re.findall(r"derived_table:([\s\n]*){([\s\n]*)sql:", view_ml)
            sql_table = re.findall(r"sql_table_name:([a-zA-Z0-9._\s\n]*);;", view_ml)

            view_type = None
            view_source_type = None
            view_source_name = None

            if derived_table_explore:
                view_type = 'derived_table'
                view_source_type = 'explore'
                view_source_name = derived_table_explore[0][2].strip()

            if derived_table_sql:
                view_type = 'derived_table'
                view_source_type = 'sql'
                view_source_name = 'custom_sql_query'

            if sql_table:
                view_type = 'sql_table'
                view_source_type = 'sql'
                view_source_name = sql_table[0].strip()

            view_info['view_type'] = view_type
            view_info['view_source_type'] = view_source_type
            view_info['view_source_name'] = view_source_name
            view_info['syntax_error'] = None

            if file_type != 'view':
                view_info['syntax_error'] = 'flagged view as created in model file'

            views_info.append(view_info)

    elif num_views == 1:
        view_info = {}
        view = views[0]
        view_info['view_name'] = view
        view_info['view_file_location'] = view_file

        view_sequence = views.index(view)

        view_ml = ml

        derived_table_explore = re.findall(r"derived_table:([\s\n]*){([\s\n]*)explore_source:([a-zA-Z0-9_\s\n]*){", view_ml)
        derived_table_sql = re.findall(r"derived_table:([\s\n]*){([\s\n]*)sql:", view_ml)
        sql_table = re.findall(r"sql_table_name:([\"a-zA-Z0-9._\s\n]*);;", view_ml)

        view_type = None
        view_source_type = None
        view_source_name = None

        if derived_table_explore:
            view_type = 'derived_table'
            view_source_type = 'explore'
            view_source_name = derived_table_explore[0][2].strip()

        if derived_table_sql:
            view_type = 'derived_table'
            view_source_type = 'sql'
            view_source_name = 'custom_sql_query'

        if sql_table:
            view_type = 'sql_table'
            view_source_type = 'sql'
            view_source_name = sql_table[0].strip()

        view_info['view_type'] = view_type
        view_info['view_source_type'] = view_source_type
        view_info['view_source_name'] = view_source_name
        view_info['syntax_error'] = None

        if file_type != 'view':
            view_info['syntax_error'] = 'flagged view as created in model file'

        views_info.append(view_info)

    return views_info

def main():
    args = parse_args()
    wd = args.wd
    model_files, view_files, docs = parse_files(wd)

    views_info = []
    explores_info = []

    '''
    get view information
     
    1. what views are there?
    2. what sources (sql/explores) do each view reference? 
    '''

    for view_file in view_files:
        view_file_ml = return_ml(view_file)
        view_file_info = get_views(view_file, 'view', view_file_ml)
        '''in the case that users are putting explores in view files - red flag this syntax'''
        model_file_info_optional = get_explores(view_file, 'view', view_file_ml)
        if model_file_info_optional:
            explores_info.extend(model_file_info_optional)
        views_info.extend(view_file_info)

    '''
    get explore information
    
    1. what explores are there?
    2. what views do each explore reference? (if no external views are referenced, the name of the view = name of explore 
    '''

    for model_file in model_files:
        model_file_ml = return_ml(model_file)
        model_file_info = get_explores(model_file, 'model', model_file_ml)
        '''in the case that users are putting views in explore files - red flag this syntax'''
        view_file_info_optional = get_views(model_file, 'model', model_file_ml)
        explores_info.extend(model_file_info)
        if view_file_info_optional:
            views_info.extend(view_file_info_optional)

    views_df = pd.DataFrame(views_info)
    explores_df = pd.DataFrame(explores_info)

    '''
    find file dependencies: cross reference explores-views and views-explores

    1. in views_df, if view references an explore, reference the explore model file name
    * for each view file, list model files that need to be included
    * for each model file, list view files that need to be included
     
    '''

    views_derived_explore = views_df.loc[(views_df['view_type'] == 'derived_table') & (views_df['view_source_type'] == 'explore')]
    views_derived_sql = views_df.loc[(views_df['view_type'] == 'derived_table') & (views_df['view_source_type'] == 'sql')]
    views_sql = views_df.loc[(views_df['view_type'] == 'sql_table')]

    views_derived_explore_join = pd.merge(views_derived_explore, explores_df[['explore_name', 'explore_file_location']], left_on='view_source_name', right_on='explore_name', how='left')

    views_df = views_df[['view_name', 'view_type', 'view_source_type', 'view_source_name', 'view_file_location', 'syntax_error']]
    explores_df = explores_df[['explore_name', 'explore_file_location', 'view_sources', 'syntax_error']]
    views_derived_explore_join = views_derived_explore_join[['view_name', 'view_type', 'view_source_type', 'view_source_name', 'view_file_location', 'explore_name', 'explore_file_location', 'syntax_error']]

    views_df.sort_values(by=['view_type', 'view_source_type', 'view_name']).to_csv('views.csv')

    views_derived_explore_join.sort_values(by=['view_type', 'view_source_type', 'view_name']).to_csv('explore_derived_views.csv')


    view_includes = views_derived_explore_join.groupby('view_file_location')['explore_file_location'].apply(list).to_frame()
    view_includes = view_includes.reset_index()
    view_includes['explore_file_location'].apply(set).to_frame()
    view_includes['explore_file_location'].apply(list).to_frame()
    view_includes.to_csv('view_includes.csv')

    model_includes_raw = explores_df.groupby('explore_file_location')['view_sources'].apply(list).to_frame()
    model_includes_raw = model_includes_raw.reset_index()
    model_includes_raw = model_includes_raw.assign(view_sources=model_includes_raw.view_sources.apply(np.concatenate))
    model_includes_raw['view_sources'].apply(set).to_frame()
    model_includes_raw['view_sources'].apply(list).to_frame()
    model_includes_df = model_includes_raw.view_sources.apply(pd.Series).merge(model_includes_raw, left_index = True, right_index = True).drop(['view_sources'], axis = 1).melt(id_vars = ['explore_file_location'], value_name = 'view_sources').drop("variable", axis = 1).dropna()
    model_includes_df_join = pd.merge(model_includes_df, views_df[['view_name', 'view_file_location']], left_on='view_sources', right_on='view_name', how='left')
    model_includes = model_includes_df_join.groupby('explore_file_location')['view_file_location'].apply(list).to_frame()
    model_includes = model_includes.reset_index()
    model_includes.to_csv('model_includes.csv')

    '''
    find explores that are not referenced by any views; these are the end points
        explores names in `explores_df` that are not in `views_derived_explore_join`
    '''

    explores_names = list(explores_df['explore_name'])
    referenced_explore_names = list(views_derived_explore_join['explore_name'].unique())

    endpoint_explores = []
    for explore_name in explores_names:
        if explore_name not in referenced_explore_names:
            endpoint_explores.append(explore_name)

    explores_df['is_endpoint_explore'] = False

    for i, row in explores_df.iterrows():
        if row['explore_name'] in endpoint_explores:
            explores_df.at[i, 'is_endpoint_explore'] = True

    explores_df.to_csv('explores.csv')

    '''
    1. for endpoint explores, list supporting views
    2. for views in 1, list supporting explores, if applicable, if not, list origin source
    3. for explores in 2, if any, list supporting views
    4. for views in 3, list supporting explores, if applicable, and if not, list origin source
    5. repeat until all view sources are origin sources
    '''

    end_explores_list = explores_df[(explores_df.is_endpoint_explore == True) | ((explores_df.explore_name == 'report_systems') & (explores_df.explore_file_location == 'marketing.model.lkml'))][['explore_name', 'view_sources']].to_dict(orient='records')
    #end_explores_list = explores_df[(explores_df.explore_name == 'report_systems') & (explores_df.explore_file_location == 'marketing.model.lkml')][['explore_name', 'view_sources']].to_dict(orient='records')
    end_explores_info = []
    for end_explore in end_explores_list:
        explore_info = {}
        explore_views = end_explore['view_sources']
        explore_views_info = []
        for explore_view in explore_views:
            recursion_cache = []
            recursion_cache.append((end_explore['explore_name'] + 'explore', explore_view + 'view'))
            explore_view_info = parse_sources(explore_view, 'view', views_df, explores_df, recursion_cache)
            explore_views_info.append(explore_view_info)
        explore_info['name'] = end_explore['explore_name']
        explore_info['type'] = 'explore'
        explore_info['children'] = explore_views_info
        end_explores_info.append(explore_info)

    json_list = []
    d3_template = 'trees/tree_template.html'

    for i in end_explores_info:
        filename = wd + '/trees/' + str(i['name']) + '.json'
        json_list.append(str(i['name']))
        with open(filename, 'w') as f:
            f.write('[\n')
            json.dump(i, f)
            f.write(']\n')

    generate_graphs(wd, json_list, d3_template)

def generate_graphs(wd, json_list, d3_template):

    with open(d3_template, 'r') as f:
        template = f.read()

    for json_file in json_list:
        tree_filename = wd + '/trees/' + json_file  + '.html'
        write_tree = template.replace('<title>LookML Tree</title>', '<title>LookML Tree: ' + json_file + '</title>')
        write_tree = write_tree.replace('treeData.json', json_file + '.json')
        with open(tree_filename, 'w') as f:
            f.write(write_tree)


def parse_sources(component, component_type, views_df, explores_df, recursion_cache):
    recursion_cache = list(set(recursion_cache))
    cache_extension = []
    if len(recursion_cache) > 1:
        for linked_item in recursion_cache:
            front_val = linked_item[0]
            end_val = linked_item[-1]
            for linked_item2 in recursion_cache:
                front_val2 = linked_item2[0]
                end_val2 = linked_item2[-1]
                if (front_val2 == front_val) & (end_val2 != end_val):
                    if (end_val2, end_val) not in recursion_cache:
                        if ((end_val2[-4:] == 'lore') & (end_val[-4:] != 'lore') or (end_val2[-4:] == 'view') & (end_val[-4:] != 'view') or (end_val2[-4:] != 'lore') & (end_val[-4:] == 'lore') or (end_val2[-4:] != 'view') & (end_val[-4:] == 'view')):
                            cache_extension.append((end_val2, end_val))
                if (front_val2 == end_val) & (end_val2 != front_val):
                    if (end_val2, front_val) not in recursion_cache:
                        if ((end_val2[-4:] == 'lore') & (front_val[-4:] != 'lore') or (end_val2[-4:] == 'view') & (
                                front_val[-4:] != 'view') or (end_val2[-4:] != 'lore') & (front_val[-4:] == 'lore') or (
                                end_val2[-4:] != 'view') & (front_val[-4:] == 'view')):
                            cache_extension.append((end_val2, front_val))
                if (end_val2 == front_val) & (front_val2 != end_val):
                    if (front_val2, end_val) not in recursion_cache:
                        if ((front_val2[-4:] == 'lore') & (end_val[-4:] != 'lore') or (front_val2[-4:] == 'view') & (
                                end_val[-4:] != 'view') or (front_val2[-4:] != 'lore') & (end_val[-4:] == 'lore') or (
                                front_val2[-4:] != 'view') & (end_val[-4:] == 'view')):
                            cache_extension.append((front_val2, end_val))
                if (end_val2 == end_val) & (front_val2 != front_val):
                    if (front_val2, front_val) not in recursion_cache:
                        if ((front_val2[-4:] == 'lore') & (front_val[-4:] != 'lore') or (front_val2[-4:] == 'view') & (
                                front_val[-4:] != 'view') or (front_val2[-4:] != 'lore') & (front_val[-4:] == 'lore') or (
                                front_val2[-4:] != 'view') & (front_val[-4:] == 'view')):
                            cache_extension.append((front_val2, front_val))
        recursion_cache.extend(cache_extension)
    component_info = {}
    component_info_list = []
    component_info['name'] = component
    component_info['type'] = component_type
    is_origin = False
    if component_type =='view':
        #recursion_cache.append(component + component_type)
        source_type = views_df['view_source_type'][views_df['view_name'] == component].to_string(index=False)
        source_name = views_df['view_source_name'][views_df['view_name'] == component].to_string(index=False)
        source_info = {}
        if source_type == 'sql':
            is_origin = True
        source_info['name'] = source_name
        source_info['type'] = source_type
        #recursion_cache.append((component + component_type, source_name + source_type))
        if is_origin == False:
            if (component + component_type, source_name + source_type) not in recursion_cache:
                recursion_cache.append((component + component_type, source_name + source_type))
                component_info['children'] = [parse_sources(source_name, source_type, views_df, explores_df, recursion_cache)]
            else:
                source_info['children'] = [{'name': 'ERROR', 'type': 'Circular Reference'}]
                component_info['children'] = [source_info]
        else:
            source_info['children'] = [{'name': 'self', 'type': 'self'}]
            component_info['children'] = [source_info]
    elif component_type == 'explore':
        view_names = explores_df['view_sources'][explores_df['explore_name'] == component].values.tolist()[0]
        view_info_list = []
        for view_name in view_names:
            recursion_cache.append((component + component_type, view_name + 'view'))
            view_info = parse_sources(view_name, 'view', views_df, explores_df, recursion_cache)
            view_info_list.append(view_info)
        component_info['children'] = view_info_list
 
    return component_info

if __name__ == "__main__":
    main()
