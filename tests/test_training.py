import os
import shutil

from nose.tools import assert_raises_regexp

from planemo import cli
from planemo import training
from planemo.bioblend import galaxy
from planemo.engine import (
    engine_context,
    is_galaxy_engine,
)
from planemo.runnable import for_path
from .test_utils import (
    PROJECT_TEMPLATES_DIR,
    TEST_DATA_DIR
)


METADATA_FP = os.path.join(TEST_DATA_DIR, "training_metadata_w_zenodo.yaml")
TRAINING_TEMPLATE_DIR = os.path.join(PROJECT_TEMPLATES_DIR, "training")
TUTORIAL_FP = os.path.join("tutorials", "tutorial1", "tutorial.md")
DATATYPE_FP = os.path.join(TEST_DATA_DIR, "training_datatypes.yaml")
ZENODO_LINK = 'https://zenodo.org/record/1321885'
GALAXY_URL = 'http://usegalaxy.eu'
WF_FP = os.path.join(TEST_DATA_DIR, "test_workflow_1.ga")

KWDS, topic_dir, tuto_dir = prepare_test()
ctx = cli.Context()
ctx.planemo_directory = "/tmp/planemo-test-workspace"
assert is_galaxy_engine(**KWDS)
runnable = for_path(WF_FP)
with engine_context(ctx, **KWDS) as galaxy_engine:
    with galaxy_engine.ensure_runnables_served([runnable]) as config:
        workflow_id = config.workflow_id(WF_FP)
        WF = config.gi.workflows.export_workflow_dict(workflow_id)


def prepare_test():
    topic_name = 'my_new_topic'
    topic_dir = topic_name
    tuto_name = "new_tuto"
    tuto_dir = os.path.join(topic_dir, "tutorials", tuto_name)
    kwds = {
        'topic_name': topic_name,
        'topic_title': "New topic",
        'topic_target': "use",
        'topic_summary': "Topic summary",
        'tutorial_name': tuto_name,
        'tutorial_title': "Title of tuto",
        'hands_on': True,
        'slides': True,
        'workflow': None,
        'workflow_id': None,
        'zenodo': None,
        'datatypes': DATATYPE_FP,
        # planemo configuation
        'conda_auto_init': True,
        'conda_auto_install': True,
        'conda_copy_dependencies': False,
        'conda_debug': False,
        'conda_dependency_resolution': False,
        'conda_ensure_channels': 'iuc,bioconda,conda-forge,defaults',
        'conda_exec': None,
        'conda_prefix': None,
        'conda_use_local': False,
        'brew_dependency_resolution': False,
        'daemon': False,
        'database_connection': None,
        'database_type': 'auto',
        'dependency_resolvers_config_file': None,
        'docker': False,
        'docker_cmd': 'docker',
        'docker_extra_volume': None,
        'docker_galaxy_image': 'quay.io/bgruening/galaxy',
        'docker_host': None,
        'docker_sudo': False,
        'docker_sudo_cmd': 'sudo',
        'engine': 'galaxy',
        'extra_tools': (),
        'file_path': None,
        'galaxy_api_key': None,
        'galaxy_branch': None,
        'galaxy_database_seed': None,
        'galaxy_email': 'planemo@galaxyproject.org',
        'galaxy_root': None,
        'galaxy_single_user': True,
        'galaxy_source': None,
        'galaxy_url': None,
        'host': '127.0.0.1',
        'ignore_dependency_problems': False,
        'install_galaxy': False,
        'job_config_file': None,
        'mulled_containers': False,
        'no_cleanup': False,
        'no_cache_galaxy': False,
        'no_dependency_resolution': True,
        'non_strict_cwl': False,
        'pid_file': None,
        'port': '9090',
        'postgres_database_host': None,
        'postgres_database_port': None,
        'postgres_database_user': 'postgres',
        'postgres_psql_path': 'psql',
        'profile': None,
        'shed_dependency_resolution': False,
        'shed_install': True,
        'shed_tool_conf': None,
        'shed_tool_path': None,
        'skip_venv': False,
        'test_data': None,
        'tool_data_table': None,
        'tool_dependency_dir': None
    }
    return (kwds, topic_dir, tuto_dir)


def test_load_yaml():
    """Test :func:`planemo.training.load_yaml`."""
    metadata = training.load_yaml(METADATA_FP)
    # test if name there
    assert metadata["name"] == "test"
    # test if order of material is conserved
    assert metadata["material"][1]["name"] == "test"


def test_save_to_yaml():
    """Test :func:`planemo.training.save_to_yaml`."""
    metadata = training.load_yaml(METADATA_FP)
    new_metadata_fp = "metadata.yaml"
    training.save_to_yaml(metadata, new_metadata_fp)
    assert os.path.exists(new_metadata_fp)
    assert open(new_metadata_fp, 'r').read().find('material') != -1
    os.remove(new_metadata_fp)


def test_get_template_dir_1():
    """Test :func:`planemo.training.get_template_dir`: test exception raising"""
    kwds = {"templates": None}
    exp_exception = "This script needs to be run in the training material repository"
    with assert_raises_regexp(Exception, exp_exception):
        training.get_template_dir(kwds)


def test_get_template_dir_2():
    """Test :func:`planemo.training.get_template_dir`: test default return value"""
    kwds = {"templates": None}
    os.makedirs("templates")
    assert training.get_template_dir(kwds) == "templates"
    shutil.rmtree("templates")


def test_get_template_dir_3():
    """Test :func:`planemo.training.get_template_dir`: test return value"""
    template_path = "temp"
    kwds = {"templates": template_path}
    assert training.get_template_dir(kwds) == template_path


def test_update_top_metadata_file_1():
    """Test :func:`planemo.training.update_top_metadata_file`: test topic change."""
    new_index_fp = "index.md"
    topic_name = 'my_new_topic'
    template_index_fp = os.path.join(TRAINING_TEMPLATE_DIR, "index.md")
    shutil.copyfile(template_index_fp, new_index_fp)
    training.update_top_metadata_file(new_index_fp, topic_name)
    assert open(new_index_fp, 'r').read().find(topic_name) != -1
    os.remove(new_index_fp)


def test_update_top_metadata_file_2():
    """Test :func:`planemo.training.update_top_metadata_file`: test tutorial change."""
    new_tuto_fp = "tutorial.md"
    topic_name = 'my_new_topic'
    tuto_name = 'my_new_tuto'
    template_tuto_fp = os.path.join(TRAINING_TEMPLATE_DIR, TUTORIAL_FP)
    shutil.copyfile(template_tuto_fp, new_tuto_fp)
    training.update_top_metadata_file(new_tuto_fp, topic_name, tuto_name=tuto_name)
    assert open(new_tuto_fp, 'r').read().find(tuto_name) != -1
    os.remove(new_tuto_fp)


def test_update_top_metadata_file_3():
    """Test :func:`planemo.training.update_top_metadata_file`: test tutorial change."""
    new_tuto_fp = "tutorial.md"
    topic_name = 'my_new_topic'
    template_tuto_fp = os.path.join(TRAINING_TEMPLATE_DIR, TUTORIAL_FP)
    shutil.copyfile(template_tuto_fp, new_tuto_fp)
    training.update_top_metadata_file(new_tuto_fp, topic_name, keep=False)
    assert not os.path.exists(new_tuto_fp)


def test_create_topic():
    """Test :func:`planemo.training.create_topic`."""
    kwds, topic_dir, tuto_dir = prepare_test()
    topic_name = kwds['topic_name']
    training.create_topic(kwds, topic_dir, TRAINING_TEMPLATE_DIR)
    # check if files has been moved and updated with topic name
    index_fp = os.path.join(topic_dir, "index.md")
    assert os.path.exists(index_fp)
    assert open(index_fp, 'r').read().find(topic_name) != -1
    tuto_fp = os.path.join(topic_dir, TUTORIAL_FP)
    assert os.path.exists(tuto_fp)
    assert open(tuto_fp, 'r').read().find(topic_name) != -1
    # check metadata content
    metadata = training.load_yaml(os.path.join(topic_dir, "metadata.yaml"))
    assert metadata['name'] == topic_name
    # check in metadata directory
    assert os.path.exists(os.path.join("metadata", "%s.yaml" % topic_name))
    # clean
    shutil.rmtree(topic_dir)
    shutil.rmtree("metadata")


def test_update_tutorial():
    """Test :func:`planemo.training.update_tutorial`."""
    kwds, topic_dir, tuto_dir = prepare_test()
    tuto_title = kwds['tutorial_title']
    metadata_fp = os.path.join(topic_dir, "metadata.yaml")
    tuto_fp = os.path.join(tuto_dir, "tutorial.md")
    slides_fp = os.path.join(tuto_dir, "slides.html")
    # create a topic and prepare the tutorial
    training.create_topic(kwds, topic_dir, TRAINING_TEMPLATE_DIR)
    template_tuto_path = os.path.join(topic_dir, "tutorials", "tutorial1")
    os.rename(template_tuto_path, tuto_dir)
    assert open(metadata_fp, 'r').read().find("tutorial1") != -1
    # test update a new tutorial
    training.update_tutorial(kwds, tuto_dir, topic_dir)
    assert open(metadata_fp, 'r').read().find("tutorial1") == -1
    assert open(metadata_fp, 'r').read().find(tuto_title) != -1
    assert os.path.exists(tuto_fp)
    assert os.path.exists(slides_fp)
    # test update an existing tutorial
    new_tuto_title = "A totally new title"
    kwds['tutorial_title'] = new_tuto_title
    kwds['slides'] = False
    training.update_tutorial(kwds, tuto_dir, topic_dir)
    assert open(metadata_fp, 'r').read().find(tuto_title) == -1
    assert open(metadata_fp, 'r').read().find(new_tuto_title) != -1
    assert not os.path.exists(slides_fp)
    # clean
    shutil.rmtree(topic_dir)
    shutil.rmtree("metadata")


def test_get_zenodo_record():
    """Test :func:`planemo.training.get_zenodo_record`."""
    z_record, req_res = training.get_zenodo_record(ZENODO_LINK)
    file_link_prefix = "https://zenodo.org/api/files/51a1b5db-ff05-4cda-83d4-3b46682f921f"
    assert z_record == "1321885"
    assert 'files' in req_res
    assert req_res['files'][0]['type'] in ['rdata', 'csv']
    assert req_res['files'][0]['links']['self'].find(file_link_prefix) != -1


def test_get_zenodo_record_with_doi():
    """Test :func:`planemo.training.get_zenodo_record`: link with DOI."""
    z_link = 'https://doi.org/10.5281/zenodo.1321885'
    z_record, req_res = training.get_zenodo_record(z_link)
    file_link_prefix = "https://zenodo.org/api/files/51a1b5db-ff05-4cda-83d4-3b46682f921f"
    assert z_record == "1321885"
    assert 'files' in req_res
    assert req_res['files'][0]['type'] in ['rdata', 'csv']
    assert req_res['files'][0]['links']['self'].find(file_link_prefix) != -1


def test_get_galaxy_datatype():
    """Test :func:`planemo.training.get_galaxy_datatype`."""
    assert training.get_galaxy_datatype("csv", DATATYPE_FP) == "csv"
    assert training.get_galaxy_datatype("test", DATATYPE_FP) == "strange_datatype"
    assert training.get_galaxy_datatype("unknown", DATATYPE_FP).find("# Please add") != -1


def test_get_files_from_zenodo():
    """Test :func:`planemo.training.get_files_from_zenodo`."""
    files, links, z_record = training.get_files_from_zenodo(ZENODO_LINK, DATATYPE_FP)
    assert z_record == "1321885"
    # test links
    file_link_prefix = "https://zenodo.org/api/files/51a1b5db-ff05-4cda-83d4-3b46682f921f"
    assert links[0].find(file_link_prefix) != -1
    # test files dict
    assert files[0]['url'].find(file_link_prefix) != -1
    assert files[0]['src'] == 'url'
    assert files[0]['info'] == ZENODO_LINK
    assert files[0]['ext'].find("# Please add") != -1
    assert files[1]['ext'] == 'csv'


def test_prepare_data_library():
    """Test :func:`planemo.training.prepare_data_library`."""
    kwds, topic_dir, tuto_dir = prepare_test()
    os.makedirs(tuto_dir)
    files, links, z_record = training.get_files_from_zenodo(ZENODO_LINK, DATATYPE_FP)
    datalib_fp = os.path.join(tuto_dir, "data-library.yaml")
    # test default prepare_data_library
    training.prepare_data_library(files, kwds, z_record, tuto_dir)
    assert os.path.exists(datalib_fp)
    datalib = training.load_yaml(datalib_fp)
    assert datalib['destination']['name'] == 'GTN - Material'
    assert datalib['items'][0]['name'] == kwds['topic_title']
    assert datalib['items'][0]['items'][0]['name'] == kwds['tutorial_title']
    assert datalib['items'][0]['items'][0]['items'][0]['name'] == "DOI: 10.5281/zenodo.%s" % z_record
    assert datalib['items'][0]['items'][0]['items'][0]['description'] == "latest"
    assert datalib['items'][0]['items'][0]['items'][0]['items'][0]['url'] == files[0]['url']
    # test adding a new collection for same tutorial
    new_z_record = '124'
    training.prepare_data_library(files, kwds, new_z_record, tuto_dir)
    datalib = training.load_yaml(datalib_fp)
    assert datalib['items'][0]['items'][0]['items'][0]['name'] == "DOI: 10.5281/zenodo.%s" % new_z_record
    assert datalib['items'][0]['items'][0]['items'][0]['description'] == "latest"
    assert datalib['items'][0]['items'][0]['items'][1]['name'] == "DOI: 10.5281/zenodo.%s" % z_record
    assert datalib['items'][0]['items'][0]['items'][1]['description'] == ""
    # test adding a new tutorial
    new_tuto_title = "New title"
    kwds['tutorial_title'] = new_tuto_title
    training.prepare_data_library(files, kwds, z_record, tuto_dir)
    datalib = training.load_yaml(datalib_fp)
    assert datalib['items'][0]['items'][1]['name'] == new_tuto_title
    assert datalib['items'][0]['items'][1]['items'][0]['name'] == "DOI: 10.5281/zenodo.%s" % z_record
    # test adding a new topic
    new_topic_title = "New title"
    kwds['topic_title'] = new_topic_title
    training.prepare_data_library(files, kwds, z_record, tuto_dir)
    datalib = training.load_yaml(datalib_fp)
    assert datalib['items'][1]['name'] == new_topic_title
    assert datalib['items'][1]['items'][0]['name'] == new_tuto_title
    assert datalib['items'][1]['items'][0]['items'][0]['name'] == "DOI: 10.5281/zenodo.%s" % z_record
    # clean
    shutil.rmtree(topic_dir)


def test_prepare_data_library_from_zenodo():
    """Test :func:`planemo.training.prepare_data_library_from_zenodo`."""
    kwds, topic_dir, tuto_dir = prepare_test()
    os.makedirs(tuto_dir)
    datalib_fp = os.path.join(tuto_dir, "data-library.yaml")
    # test prepare_data_library_from_zenodo with no zenodo
    links = training.prepare_data_library_from_zenodo(kwds, tuto_dir)
    assert len(links) == 0
    assert not os.path.exists(datalib_fp)
    # test prepare_data_library_from_zenodo with a zenodo link
    kwds['zenodo'] = ZENODO_LINK
    links = training.prepare_data_library_from_zenodo(kwds, tuto_dir)
    file_link_prefix = "https://zenodo.org/api/files/51a1b5db-ff05-4cda-83d4-3b46682f921f"
    assert links[0].find(file_link_prefix) != -1
    assert os.path.exists(datalib_fp)
    # clean
    shutil.rmtree(topic_dir)


def test_get_wf_tool_description():
    """Test :func:`planemo.training.get_wf_tool_description`."""
    gi = galaxy.GalaxyInstance(GALAXY_URL)
    tools = training.get_wf_tool_description(WF, gi)
    print(tools)
    assert 1==2


def test_get_wf_from_running_galaxy():
    """Test :func:`planemo.training.get_wf_from_running_galaxy`."""
    assert 1==2
    training.get_wf_from_running_galaxy(KWDS)


def test_format_inputs():
    """Test :func:`planemo.training.format_inputs`."""
    wf_inputs = {
        "input1": {"id": 0, "output_name": "output"}, 
        "queries_0|input2": {"id": 1, "output_name": "output"}
    }
    gi = galaxy.GalaxyInstance(GALAXY_URL)
    cat_desc = gi.tools.show_tool("cat1", io_details=True)
    training.format_inputs(wf_inputs, tp_desc, wf_steps, level)

    # {{space}}- {{ '{%' }} icon {{icon}} {{ '%}' }} *"{{input_name}}"*: {{input_value}}


def test_get_input_tool_name():
    """Test :func:`planemo.training.get_input_tool_name`."""
    steps = {'1': {'name': 'Input dataset'}}
    # test if step not found
    tool_name = training.get_input_tool_name(2, steps)
    assert tool_name == ''
    # test if tool is input
    tool_name = training.get_input_tool_name(1, steps)
    assert tool_name == '(input dataset)'
    # test if other case
    steps['1']['name'] = 'Tool name'
    tool_name = training.get_input_tool_name(1, steps)
    assert tool_name == '(output of **Tool name** {% icon tool %})'


def test_get_tool_input():
    """Test :func:`planemo.training.get_tool_input`."""
    tool_desc = {
        'inputs': [
            {'name': "name1", 'content': 'c'},
            {'name': "name2", 'content': 'c'}
        ]
    }
    tool_inp = training.get_tool_input(tool_desc)
    assert "name1" in tool_inp
    assert 'content' in tool_inp["name1"]
    assert tool_inp["name1"]['content'] == 'c'