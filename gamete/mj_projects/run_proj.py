"""This module does A and B.
Etc.
"""
#===============================================================================
# Set up
#===============================================================================
# Standard:
from __future__ import division
from __future__ import print_function
import time
import itertools

#===============================================================================
# Internal
#===============================================================================
import deap as dp
import deap.design_space as ds
import deap.mj_utilities.util_db_process as util_proc
from deap.mj_utilities.db_base import DB_Base

#===============================================================================
# External
#===============================================================================
import numpy as np
import sqlalchemy as sa
import sqlalchemy.orm as sa_orm

#===============================================================================
# Utilities
#===============================================================================
#from utility_inspect import whoami, whosdaddy, listObject
from ExergyUtilities import utility_SQL_alchemy as util_sa
from ExergyUtilities import utility_excel as util_excel
from ExergyUtilities import utility_path as util_path
from ExergyUtilities import utility_GUI as util_gui
#===============================================================================
# Standard library
#===============================================================================
import importlib
import cProfile
import shutil
import sys
import unittest
import os

#===============================================================================
# Logging
#===============================================================================
import logging.config
from UtilityLogger import loggerCritical,loggerDebug

#===============================================================================
#--- Settings
#===============================================================================
def get_settings(book):
    with loggerCritical():
        all_data = book.get_table("Project")
    all_data = zip(*all_data)
    
    settings = book.get_row_as_dict(all_data,1)
    settings['excel_path'] = book.excelPath
    
    return settings

def build_structure(settings):
    
    if settings['continue_run'] == 'Yes':
        
        # Get the path of the excel file, which is always stored at the root of project
        settings['run_full_path'] = os.path.split(settings['excel_path'])[0]
        
        #run_root_directory
        assert(os.path.exists(settings['run_root_directory']))
        
        path_sql = os.path.join(settings['run_full_path'],'SQL','')
        path_sql_db = os.path.join(path_sql, 'results.sql')
        settings['path_sql_db'] = path_sql_db
        
        path_mlab = os.path.join(settings['run_root_directory'],'Matlab')
        settings['path_matlab'] = path_mlab
        
        settings['path_evolog'] = os.path.join(settings['run_full_path'],'evolog.txt')
        
        assert os.path.exists(settings['run_root_directory']), "{}".format(settings['run_root_directory'])
        assert os.path.isfile(settings['path_sql_db']), "{}".format(settings['path_sql_db'])
        settings['existing_db'] = 'Yes'
        assert os.path.exists(settings['run_full_path']), "{}".format(settings['path_matlab'])
        assert os.path.isfile(settings['path_evolog']), "{}".format(settings['path_evolog'])
        
        assert os.path.isfile(settings['path_opt_front']), "{}".format(settings['path_evolog'])
        
        return settings
    
    elif settings['delete_folder']== 'Yes':
        raise
    else:
        pass
    
    #===========================================================================
    # Check root
    #===========================================================================
    if not os.path.exists(settings['run_root_directory']):
        os.makedirs(settings['run_root_directory'])
    
    #===========================================================================
    # Create sub dir for run
    #===========================================================================
    if settings['version_folders'] == 'Yes':
        this_rev_num = util_path.get_next_rev_number_dir(settings['run_root_directory'],settings['run_name'])
        this_rev_text = "{0:03d}".format(this_rev_num)
        path_run = os.path.join(settings['run_root_directory'], settings['run_name'] + this_rev_text)
        path_run = os.path.abspath(path_run)
        assert not os.path.exists(path_run), "{} exists".format(path_run)
        os.makedirs(path_run)
        settings['run_full_path'] = path_run
    else: 
        raise

    #===========================================================================
    # Create dirs of SQL and Matlab
    #===========================================================================
    path_sql = os.path.join(path_run,'SQL')
    #print(path_sql)
    if not os.path.exists(path_sql):
        os.makedirs(path_sql)
    path_sql_db = os.path.join(path_sql, 'results.sql')
    settings['path_sql_db'] = path_sql_db
    settings['existing_db'] = 'No'

    path_mlab = os.path.join(path_run,'Matlab')
    #print(path_sql)
    if not os.path.exists(path_mlab):
        os.makedirs(path_mlab)
    settings['path_matlab'] = path_mlab
    
    
    #===========================================================================
    # Copy over the project definition file
    #===========================================================================
    settings['path_run_definition_book'] = os.path.join(path_run,'definition.xlsx')
    shutil.copyfile(settings['path_book'], settings['path_run_definition_book'])
    
    #===========================================================================
    # Evolog
    #===========================================================================
    settings['path_evolog'] = os.path.join(path_run,'evolog.txt')
    
    return settings

#===============================================================================
#---Algorithm
#===============================================================================
def get_operators(book):
    with loggerCritical():
        all_data = book.get_table("Operators")
        
    operators_def = dict()
    #print(all_data)
    for row in all_data:
        operators_def[row[0]] = {'module' : row[1],'function' : row[2]}

    for k,v in operators_def.iteritems():
        #this_mod = importlib.import_module('deap.' + operators_def[k]['module'])
        operators_def[k] = getattr(importlib.import_module('deap.' + operators_def[k]['module']), operators_def[k]['function'])

    logging.debug("Operators loaded:")
    for item,function in operators_def.iteritems():
        logging.debug("{:>20} - {}".format(item,function.__name__))
                
    return operators_def
#     raise        
#     operators = list()
#     for operator_name in all_data[1:]:
#         name = operator_name[0]
#         operators_module = importlib.import_module('deap.mj_operators')
#         operator_function = getattr(operators_module,name)
#         logging.debug("Loaded {} operator".format(operator_function.__name__))
#         operators.append(operators_module)
#     return operators

def get_algorithm(book):
    with loggerCritical():
        all_data = book.get_table("Algorithm")
    
    algorithm_def = dict()
    for row in all_data:
        algorithm_def[row[0]] = {'module' : row[1],'function' : row[2]}
        
    for k,v in algorithm_def.iteritems():
        #this_mod = importlib.import_module('deap.' + algorithm_def[k]['module'])
        algorithm_def[k] = getattr(importlib.import_module('deap.' + algorithm_def[k]['module']), algorithm_def[k]['function'])
        
    logging.debug("Algorithm loaded:")
    for item,function in algorithm_def.iteritems():
        logging.debug("{:>20} - {}".format(item,function))

    return algorithm_def


def get_parameters(book):
    with loggerCritical():
        all_data = book.get_table("Parameters")
    
    parameters_def = dict()
    for row in all_data[1:]:
        parameters_def[row[0]] = {'value' : row[1],'type' : row[2]}
    
    for k,v in parameters_def.iteritems():
        if v['type'] == 'int':
            parameters_def[k] = int(v['value'])
        elif v['type'] == 'float':
            parameters_def[k] = v['value']       
        else:
            
            raise Exception("Unknown {}".format(v['type']))

    
    #print(parameters_def)
    #raise
    #settings = book.get_row_as_dict(all_data,1)
    
    return parameters_def

#===============================================================================
#--- Get mapping 
#===============================================================================
def get_list_variables(book):
    all_data = book.get_table("List Variables")
    if len(all_data) == 1:
        return None
    variable_rows = [row for row in all_data[2:] if row[0]]
    row_nums = (xrange(1, 2+len(variable_rows)))
    
    variables = list()
    for i, rownum in enumerate(row_nums):
        variable_def = book.get_row_as_dict(all_data,rownum, num_cols = 3, flg_length_mismatch = False)
        list_vals = [item for item in all_data[rownum] if item != ""]
        list_vals = list_vals[3:]
        thisVar = ds.Variable.ordered(variable_def['Name'],variable_def['Type'],list_vals)
        variables.append(thisVar)

    return variables


def get_range_variables(book):
    all_data = book.get_table("Range Variables")
    variable_rows = [row for row in all_data[2:] if row[0]]
    row_nums = (xrange(1, 2+len(variable_rows)))

    variables = list()
    for i, rownum in enumerate(row_nums):
        variable_def = book.get_row_as_dict(all_data,rownum, flg_length_mismatch = True)
        thisVar = ds.Variable.from_range(variable_def['Name'], variable_def['Type'], str(variable_def['MIN']), str(variable_def['STEP']), str(variable_def['MAX']))
        variables.append(thisVar)

    return variables

def get_fitness(book):
    with loggerCritical():
        all_data = book.get_table("Objectives")
    objective_rows = [row for row in all_data[1:] if row[0]]
    #print(objective_rows)
    row_nums = (xrange(1, 1+len(objective_rows)))
    
    names = list()
    weights = list()
    for rownum in row_nums:
        obj_def = book.get_row_as_dict(all_data,rownum, flg_length_mismatch = True)
        #print(obj_def)
        names.append(obj_def['Name'])
        weights.append(float(obj_def['Weight']))

    dp.creator.create("Fitness", dp.base.Fitness, weights=(-1.0, -1.0), names = ('obj1', 'obj2'))
    
    #print(globals())
    raise
    return dp.creator.Fitness
        
    #ds.Fitness(weights=weights, names=names)


def get_objectives(fitness):
    # Create OSpace from Fitness
    objs = list()
    for name,weight in zip(fitness.names,fitness.weights):
        objs.append(ds.Objective(name,weight))

    return objs

#-- Extra
def my_range(start, stop, step):
    this_list = [float(num) for num in np.arange(start, stop, step)] + [stop] 
    return this_list

def parameterize_excel_def_from_table(template_path,target_path,def_table):
    for i,this_def in enumerate(def_table):
        name = 'Definition'+str(i)+'.xlsx'
        with util_excel.ExcelBookAPI(template_path) as book:            
            this_target_path = os.path.join(target_path,name)
        this_book = book.clone(this_target_path)        
        for mod in this_def:
            print('This mod: {}'.format(mod))
            print('This book: {}'.format(this_book))
            target_row = this_book.scanDown2(mod[0], 1, 1, mod[1], limitScan=100)
            target_col = 2
            this_book.write_one(mod[0],target_row,target_col,mod[2])
        this_book.save_and_close_no_warnings()
            
def parameterize_excel_def_from_dicts(template_path,target_path,def_table):
    for i,this_def in enumerate(def_table):
        name = 'Definition'+str(i)+'.xlsx'
        with util_excel.ExcelBookAPI(template_path) as book:            
            this_target_path = os.path.join(target_path,name)
        this_book = book.clone(this_target_path)
        
        for mod in this_def:
            #print('This mod: {}'.format(mod))
            #print('This book: {}'.format(this_book))
            with loggerCritical():
                target_row = this_book.scanDown2(mod['Sheet'], 1, 1, mod['Parameter'], limitScan=100)
                target_col = 2
                this_book.write_one(mod['Sheet'], target_row, target_col, mod['Value'])
        this_book.save_and_close_no_warnings()
        
        print('Parameterized this book: {}'.format(this_book))
        


#===============================================================================
#--- Main: Get project, run, post
#===============================================================================

def run_project_def(path_book):
    with util_excel.ExcelBookRead2(path_book) as book:
             
        print("Running this book: {}".format(book))
        start_time = time.time()
        
        #===========================================================================
        #---Settings; get_settings(book)
        #===========================================================================
        settings = get_settings(book)
        settings['path_book'] = path_book
        
        settings = build_structure(settings)
        
        for k,v, in settings.iteritems():
           print("{:>30} : {:<30} {}".format(k,v, type(v)))
        
        #===========================================================================
        #---Database; session = Session()
        #===========================================================================
        if settings['in_memory'] == 'Yes':
            engine = sa.create_engine("sqlite:///{}".format(':memory:'), echo=0, listeners=[util_sa.ForeignKeysListener()])
            logging.debug("Initialized session {} with SQL alchemy version: {}".format(engine, sa.__version__))
            
        elif settings['in_memory'] == 'No':            
            engine = sa.create_engine("sqlite:///{}".format(settings['path_sql_db']), echo=0, listeners=[util_sa.ForeignKeysListener()])
            logging.debug("Initialized session {} with SQL alchemy version: {}".format(engine, sa.__version__))
        else:
            raise
        
        print("**************",engine)
        Session = sa.orm.sessionmaker(bind=engine)
        session = Session()
        
    
        with open(settings['path_evolog'], 'w+') as evolog:
            print("Start log", file=evolog)
        
        
        #===========================================================================
        #---D/O space; get_list_variables(), get_fitness(), session.add_all()
        #===========================================================================
        with loggerCritical():
            variables = list()
            list_vars = get_list_variables(book)
            if list_vars:
                variables.extend(list_vars)
            range_vars = variables.extend(get_range_variables(book))
            if range_vars:
                variables.extend(range_vars)
        
        design_space = ds.DesignSpace(variables)
        
        # Get ObjectiveSpace
        Fitness = get_fitness(book)
        
        objs = get_objectives(Fitness)
        objective_space = ds.ObjectiveSpace(objs)
    
        # Add vectors to DB
        if settings['existing_db'] == 'No':
            for var in design_space.basis_set:
                session.add_all(var.variable_tuple)
            session.add_all(objs)    
        
            # Add the variable names to the DB
            session.add_all(design_space.basis_set)
        
        #===========================================================================
        #---Operators; get_operators(book)
        #===========================================================================
        operators = get_operators(book)
    
        #===========================================================================
        #---Algorithm; get_algorithm(book)
        #===========================================================================
    
        algorithm = get_algorithm(book)
        
        parameters = get_parameters(book)
        for k,v, in parameters.iteritems():
           print("{:>30} : {:<30} {}".format(k,v, type(v)))
        
    #===========================================================================
    #---GUI; empty
    #===========================================================================
    #util_gui.simpleYesNo(question="Question; Yes or No?")
    
    #===========================================================================
    #---Mapping; 
    #===========================================================================
    mapping = ds.Mapping(design_space, objective_space)
    res_ORM_table = ds.generate_individuals_table(mapping)
    Results = ds.generate_ORM_individual(mapping)
    sa.orm.mapper(Results, res_ORM_table) 

    DB_Base.metadata.create_all(engine)
    session.commit()
    mapping.assign_fitness(Fitness)
    mapping.assign_individual(ds.individual)
    mapping.assign_evaluator(algorithm['life_cycle'])

    
    #===========================================================================
    #---Execute; algorithm['name']() 
    #===========================================================================
    algorithm['name'](settings=settings, 
                      algorithm=algorithm,
                      parameters=parameters,
                      operators=operators, 
                      mapping=mapping, 
                      session=session,
                      Results=Results)
     
    #===========================================================================
    #--Post process; util_proc
    #===========================================================================
    
    util_proc.process_run_def(settings['path_run_definition_book'],settings['path_matlab'])
    util_proc.process_db_to_mat(settings['path_sql_db'],settings['path_matlab'],settings['path_opt_front '])
    
    elapsed = time.time() - start_time
    logging.debug("Finished run after {} seconds".format(elapsed))
