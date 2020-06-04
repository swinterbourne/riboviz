# Run UMI extraction, deduplication and demultiplexing examples

Examples of configurations that request that the RiboViz workflow do UMI extraction and deduplication and also demultiplexing of multiplexed data are provided. These use [Simulated FASTQ test files](../reference/data.md#simulated-fastq-test-files) located within `data/simdata/`.

## UMI extraction and deduplication

`vignette/simdata_umi_config.yaml` has a sample configuration file which runs an analysis of `data/simdata/umi5_umi3_umi_adaptor.fastq` with UMI extraction and deduplication enabled.

To run this example using the RiboViz Python workflow:

```console
$ python -m riboviz.tools.prep_riboviz -c vignette/simdata_umi_config.yaml 
```

To run this example using the RiboViz Nextflow workflow:

```console
$ nextflow run prep_riboviz.nf -params-file vignette/simdata_umi_config.yaml -ansi-log false
```

## Barcode and UMI extraction, demultiplexing and deduplication

`vignette/simdata_multiplex_config.yaml` has a sample configuration file which runs an analysis of `data/simdata/multiplex.fastq` with barcode and UMI extraction, demultiplexing and deduplication enabled.

To run this example using the RiboViz Python workflow:

```console
$ python -m riboviz.tools.prep_riboviz -c vignette/simdata_multiplex_config.yaml 
```

To run this example using the RiboViz Nextflow workflow:

```console
$ nextflow run prep_riboviz.nf -params-file vignette/simdata_multiplex_config.yaml -ansi-log false
```