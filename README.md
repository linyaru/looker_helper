# Looker Architecture

Call LookML repository parser: `python lookml_parser.py -wd [lookml directory]`

LookML dependencies: (/helper_files)
* `views.csv`
* `explores.csv`
* `view_includes.csv`
* `model_includes.csv`

LookML model tree visualizations:
https://s3.amazonaws.com/looker-helper/index.html

## Parsing Relationships from LookML

While LookML enables on-the-fly data modelling, it is notorious for creating models that are dependent on several `SQL table > View > Auxiliary Explore > View (NDT) > Explore` iterations. To make development in LookerML easier for developers by being able to reference documented dependencies while creating new explores, this dependency parser (`lookml_parser.py`) reads LookML files in a repository and produces the following information:

### 1. List of Views (`views.csv`)
Names of all views contained in `.view.lkml` files, the files in whether they are located, whether they are sql or derived tables, and if they are derived tables, whether they use SQL or explores, and if they are derived from explores, the name of that derived explore:

`view name`
`view type`
`view source type`
`view file location`
`syntax error`

The parser also identifies syntactical inconsistencies such as creating Views within Mode files.

### 2. List of Explores (`explores.csv`)
Names of all explores contained in `.model.lkml` files, the files in which they are located, and all views referenced by the explore:

`explore name`
`explore file location`
`view sources`
`syntax error`
`is endpoint explore`

The parser also identifies syntactical inconsistencies such as creating Model within View files.

### 3. List of Views derived from Explores (explore_derived_views.csv)
Specifically - all of the information about views, plus the .model.lkml file in which the referenced explore can be found

### 4. View and Model Includes
Subsequently, the parser sorts through all of the above information and generates the list of model file names that need to be included in each view file:

(`view_includes.csv`)

`view file location`
`explore file location`

As well as view file names that need to be included in each model file:

(`model_includes.csv`)

`explore file location`
`view file location`

This parser can be run as many times as required as the repository changes. Currently, these dependencies are in text form, but the eventual goal is to identify the `Explore <- view <- explore <- view <- sql` table relationships in linked list form and that could be easily done by iterating through the existing data frames. 

## Visualizing Hierarchies

The parser steps through the first-degree dependencies generated above to generate full tree visualizations for each model (D3.js).

