"""
Command Line Interface to AmiGO
-----------------------------

"""
import logging
import os
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, TextIO, Tuple, Any, Type

import click
from go_library.amigo_solr.engine import create_handle
from go_library.datamodel.amigo_solr_api import AmigoSolrAPI, Annotation
from linkml_solr import SolrQueryEngine
from oaklib.implementations.aggregator.aggregator_implementation import AggregatorImplementation
from oaklib.interfaces import BasicOntologyInterface, OntologyInterface, ValidatorInterface, SubsetterInterface
from oaklib.io.streaming_csv_writer import StreamingCsvWriter
from oaklib.io.streaming_yaml_writer import StreamingYamlWriter
from oaklib.resource import OntologyResource
from oaklib.selector import get_resource_from_shorthand, get_implementation_from_shorthand
from oaklib.cli import input_option, output_option, output_type_option, add_option, input_type_option

@dataclass
class Settings:
    impl: Any = None
    api: AmigoSolrAPI = None


settings = Settings()

# AmiGO SOLR options

isa_partof_closure_option = click.option(
    "-A", "--isa-partof-closure",
    help="Fetch all descendants of this ID."
)
taxon_option = click.option(
    "-T", "--taxon",
    help="Taxon (direct)."
)


@click.group()
@click.option("-v", "--verbose", count=True)
@click.option("-q", "--quiet")
@input_option
@add_option
def main(verbose: int, quiet: bool, input: str, add: List):
    """Run the oaklib Command Line.

    A subcommand must be passed - for example: ancestors, terms, ...

    Most commands require an input ontology to be specified:

        runoak -i <INPUT SPECIFICATION> SUBCOMMAND <SUBCOMMAND OPTIONS AND ARGUMENTS>

    Get help on any command, e.g:

        runoak viz -h
    """
    if verbose >= 2:
        logging.basicConfig(level=logging.DEBUG)
    elif verbose == 1:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)
    if quiet:
        logging.basicConfig(level=logging.ERROR)
    resource = OntologyResource()
    resource.slug = input

    if input:
        impl_class: Type[OntologyInterface]
        resource = get_resource_from_shorthand(input)
        impl_class = resource.implementation_class
        logging.info(f'RESOURCE={resource}')
        settings.impl = impl_class(resource)
    if add:
        impls = [get_implementation_from_shorthand(d) for d in add]
        if settings.impl:
            impls = [settings.impl] + impls
        settings.impl = AggregatorImplementation(implementations=impls)
    settings.api = create_handle()

@main.command()
@click.argument("terms", nargs=-1)
@isa_partof_closure_option
@output_type_option
#@output_option
def qterm(terms, output_type, **kwargs):
    api = settings.api
    if output_type and output_type == 'csv':
        w = StreamingCsvWriter()
    else:
        w = StreamingYamlWriter()
    for r in api.query_OntologyClass(id=list(terms), **kwargs):
        w.emit(r)


@main.command()
@click.argument("terms", nargs=-1)
@isa_partof_closure_option
@output_type_option
def qgene(terms, output_type, **kwargs):
    api = settings.api
    if output_type and output_type == 'csv':
        w = StreamingCsvWriter()
    else:
        w = StreamingYamlWriter()

    for r in api.query_Bioentity(bioentity=list(terms), **kwargs):
        w.emit(r)


@main.command()
@click.argument("terms", nargs=-1)
@isa_partof_closure_option
@taxon_option
@output_type_option
def qassoc(terms, output_type, **kwargs):
    api = settings.api
    if output_type and output_type == 'csv':
        w = StreamingCsvWriter()
    else:
        w = StreamingYamlWriter()

    for r in api.query_Annotation(**kwargs):
        w.emit(r)


@main.command()
@click.argument("terms", nargs=-1)
@isa_partof_closure_option
@taxon_option
@output_type_option
def map2slim(terms, output_type, **kwargs):
    api = settings.api
    oi = settings.impl
    if output_type and output_type == 'csv':
        w = StreamingCsvWriter()
    else:
        w = StreamingYamlWriter()
    sqe: SolrQueryEngine = api.query_engine
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    results = sqe.search(Annotation,
                         solr_params={'fl': 'id,bioentity,isa_partof_closure'},
                         **kwargs)
    for r in results.items:
        w.emit(r)

if __name__ == "__main__":
    main()
