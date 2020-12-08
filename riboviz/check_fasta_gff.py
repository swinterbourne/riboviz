"""
Functions to check FASTA and GFF files for compatibility.
"""
import bisect
import warnings
from Bio import SeqIO
import gffutils
import pandas as pd
from riboviz.fasta_gff import CDS_FEATURE_FORMAT
from riboviz.fasta_gff import START_CODON
from riboviz.fasta_gff import STOP_CODONS
from riboviz.get_cds_codons import get_feature_id
from riboviz.get_cds_codons import sequence_to_codons
from riboviz import provenance

SEQUENCE = "Sequence"
""" FASTA-GFF compatibility column name (sequence ID). """
FEATURE = "Feature"
""" FASTA-GFF compatibility column name (feature ID). """
WILDCARD = "*"
"""
Name for sequences or features in issues that apply to multiple
sequences or features.
"""
NOT_APPLICABLE = ""
"""
Name for sequences or features in issues that apply exclusively
to features or sequences only.
"""
ISSUE_TYPE = "Issue"
""" FASTA-GFF compatibility column name (issue type). """
ISSUE_DATA = "Data"
""" FASTA-GFF compatibility column name (issue data). """
INCOMPLETE_FEATURE = "IncompleteFeature"
""" FASTA-GFF compatibility issue column value. """
NO_START_CODON = "NoStartCodon"
""" FASTA-GFF compatibility issue column value. """
NO_STOP_CODON = "NoStopCodon"
""" FASTA-GFF compatibility issue column value. """
INTERNAL_STOP_CODON = "InternalStopCodon"
""" FASTA-GFF compatibility issue column value. """
NO_ID_NAME = "NoIdName"
""" FASTA-GFF compatibility issue column value. """
DUPLICATE_FEATURE_ID = "DuplicateFeatureId"
""" FASTA-GFF compatibility issue column value. """
DUPLICATE_FEATURE_IDS = "DuplicateFeatureIds"
""" FASTA-GFF compatibility issue column value. """
MULTIPLE_CDS = "MultipleCDS"
""" FASTA-GFF compatibility issue column value. """
SEQUENCE_NOT_IN_FASTA = "SequenceNotInFASTA"
""" FASTA-GFF compatibility issue column value. """
SEQUENCE_NOT_IN_GFF = "SequenceNotInGFF"
""" FASTA-GFF compatibility issue column value. """
ISSUE_FORMATS = {
    INCOMPLETE_FEATURE: "Sequence {sequence} feature {feature} has length not divisible by 3",
    NO_START_CODON: "Sequence {sequence} feature {feature} doesn't start with a recognised start codon but with {data}",
    NO_STOP_CODON: "Sequence {sequence} feature {feature} doesn't end with a recognised stop codon but with {data}",
    INTERNAL_STOP_CODON: "Sequence {sequence} feature {feature} has an internal stop codon",
    NO_ID_NAME: "Sequence {sequence} feature {feature} has no 'ID' or 'Name' attribute",
    DUPLICATE_FEATURE_ID: "Sequence {sequence} has non-unique 'ID' attribute {feature}",
    MULTIPLE_CDS: "Sequence {sequence} has multiple CDS ({data} occurrences)",
    SEQUENCE_NOT_IN_FASTA: "Sequence {sequence} in GFF file is not in FASTA file",
    SEQUENCE_NOT_IN_GFF: "Sequence {sequence} in FASTA file is not in GFF file",
    DUPLICATE_FEATURE_IDS: "Non-unique 'ID' attribute {feature} ({data} occurrences)"
}
""" Format strings for printing compatibility issues. """


def get_fasta_sequence_ids(fasta):
    """
    Get a list of the unique IDs of sequences in a FASTA file.

    :param fasta: FASTA file
    :type fasta: str or unicode
    :return: Unique sequence IDs
    :rtype: set(str or unicode)
    """
    seq_ids = set()
    with open(fasta, "r") as f:
        # 'fasta' is https://biopython.org/wiki/SeqIO file type.
        for record in SeqIO.parse(f, "fasta"):
            seq_ids.add(record.id)
    return seq_ids


def get_fasta_gff_cds_issues(fasta,
                             gff,
                             feature_format=CDS_FEATURE_FORMAT,
                             use_feature_name=False,
                             start_codons=[START_CODON]):
    """
    Check FASTA and GFF files for compatibility and return a list of
    issues for relating to coding sequences, ``CDS``, features. A list
    of tuples of form (sequence ID, feature ID ('' if not applicable
    to the issue), issue type, issue data) is returned.

    The sequence ID is one of:

    * Value of sequence ID.
    * :py:const:`WILDCARD` if the issue relates to multiple
      sequences.

    The feature ID is one of:

    * :py:const:`NOT_APPLICABLE` if the issue relates to the sequence,
    * not the feature.
    * :py:const:`WILDCARD` if the issue relates to multiple features.
    * Value of ``ID`` attribute for feature, if defined and if
      ``Name`` is not defined, or ``Name`` is defined and
      ``use_feature_name`` is ``False``.
    * Value of ``Name`` attribute for feature, if defined, and if
      ``ID`` is undefined or if ``ID`` is defined and ``use_feature_name``
    is ``True``.
    * Sequence ID formatted using ``feature_format`` (default
      py:const:`CDS_FEATURE_FORMAT`) if both ``ID`` and ``Name`` are
      undefined.

    The following issue types are reported for CDSs defined in the GFF
    file:

    * :py:const:`INCOMPLETE_FEATURE`: The CDS has a length not
      divisible by 3.
    * :py:const:`NO_START_CODON`: The CDS does not start
      with a start codon (``ATG`` or those in `start_codons`)). The
      supplementary issue data is the actual codon found.
.    * :py:const:`NO_STOP_CODON`: The CDS does not end with
      a stop codon  (``TAG``, ``TGA``, ``TAA``). The supplementary
      issue data is the actual codon found.
    * :py:const:`INTERNAL_STOP_CODON`: The CDS has internal
      stop codons.
    * :py:const:`NO_ID_NAME`: The CDS has no ``ID`` or ``Name``
      attribute.
    * :py:const:`DUPLICATE_FEATURE_ID`: The CDS has a non-unique ``ID``
      attribute (attributes are expected to be unique within the scope
      of a GFF file).
    * :py:const:`DUPLICATE_FEATURE_IDS`: Related to the above,
      multiple CDSs have non-unique ``ID`` attributes. This summarises
      the count of all CDSs that share a common ``ID`` attribute. For
      this issue, the sequence ``ID`` attribute is
      :py:const:`WILDCARD`. The supplementary issue data is a
      count of the number of features with the same ID.

    The following issues are reported for sequences defined in the GFF file:

    * :py:const:`MULTIPLE_CDS`: The sequence has multiple CDS.
      For this issue, the feature ``ID`` attribute is
      :py:const:`WILDCARD`. The supplementary issue data is a count
      of the number of CDSs found.
    * :py:const:`SEQUENCE_NOT_IN_FASTA`: The sequence has a feature in
      the GFF file but the sequence is not in the FASTA file. For this
      issue, the feature ``ID`` attribute is
      py:const:`NOT_APPICABLE`.
    * :py:const:`SEQUENCE_NOT_IN_GFF`: The sequence is in the FASTA
      file but has no features in the GFF file. For this issue, the
      feature ``ID`` attribute is py:const:`NOT_APPICABLE`.

    Issue data is supplementary data relating to the issue. Unless
    already noted above this will be ``None``.

    :param fasta: FASTA file
    :type fasta: str or unicode
    :param gff: GFF file
    :type gff: str or unicode
    :param feature_format: Feature name format for features which \
    do not define ``ID``  or ``Name`` attributes. This format is \
    applied to the sequence ID to create a feature name.
    :type feature_format: str or unicode
    :param use_feature_name: If a feature defines both ``ID`` and \
    ``Name`` attributes then use ``Name` in reporting, otherwise use \
    ``ID``.
    :type use_feature_name: bool
    :param start_codons: Allowable start codons.
    :type start_codons: list(str or unicode)
    :return: List of unique sequence IDs in GFF file and list \
    of issues for sequences and features.
    :rtype: list(tuple(str or unicode, str or unicode, str or unicode, *))
    """
    gffdb = gffutils.create_db(gff,
                               dbfn='gff.db',
                               force=True,
                               keep_order=True,
                               merge_strategy='merge',
                               sort_attribute_values=True)
    issues = []
    # Track IDs of features encountered. Each ID must be unique within
    # a GFF file. See http://gmod.org/wiki/GFF3.
    feature_ids = {}
    # Track sequences encountered and counts of features for
    # each.
    sequence_features = {}
    for feature in gffdb.features_of_type('CDS'):
        if feature.seqid not in sequence_features:
            sequence_features[feature.seqid] = 0
        sequence_features[feature.seqid] += 1

        feature_id = None
        if "ID" in feature.attributes:
            feature_id = feature.attributes["ID"][0].strip()
            if feature_id in feature_ids:
                feature_ids[feature_id].append(feature.seqid)
            else:
                feature_ids[feature_id] = [feature.seqid]
        feature_id_name = get_feature_id(feature, use_feature_name)
        if feature_id_name is None:
            feature_id_name = feature_format.format(feature.seqid)
            issues.append((feature.seqid, feature_id_name,
                           NO_ID_NAME, None))
        try:
            sequence = feature.sequence(fasta)
        except KeyError as e:
            issues.append((feature.seqid,
                           NOT_APPLICABLE,
                           SEQUENCE_NOT_IN_FASTA,
                           None))
            continue
        except Exception as e:
            warnings.warn(str(e))
            continue

        seq_len_remainder = len(sequence) % 3
        if seq_len_remainder != 0:
            issues.append((feature.seqid, feature_id_name,
                           INCOMPLETE_FEATURE, None))
            sequence += ("N" * (3 - seq_len_remainder))

        sequence_codons = sequence_to_codons(sequence)
        if sequence_codons[0] not in start_codons:
            issues.append((feature.seqid, feature_id_name,
                           NO_START_CODON, sequence_codons[0]))
        if not sequence_codons[-1] in STOP_CODONS:
            issues.append((feature.seqid, feature_id_name,
                           NO_STOP_CODON, sequence_codons[-1]))
        if any([codon in STOP_CODONS
                for codon in sequence_codons[:-1]]):
            issues.append((feature.seqid, feature_id_name,
                           INTERNAL_STOP_CODON, None))

    for sequence, count in list(sequence_features.items()):
        if count > 1:
            # Insert issue, respect ordering by sequence ID.
            bisect.insort(issues, (sequence, WILDCARD, MULTIPLE_CDS, count))

    for feature_id, seq_ids in feature_ids.items():
        if len(seq_ids) > 1:
            issues.append((WILDCARD, feature_id,
                           DUPLICATE_FEATURE_IDS, len(seq_ids)))
            for seq_id in seq_ids:
                # Insert issue, respect ordering by sequence ID.
                bisect.insort(issues, (seq_id, feature_id,
                                       DUPLICATE_FEATURE_ID, None))

    gff_seq_ids = set(sequence_features.keys())
    fasta_seq_ids = get_fasta_sequence_ids(fasta)
    fasta_only_seq_ids = fasta_seq_ids - gff_seq_ids
    for seq_id in fasta_only_seq_ids:
        issues.append((seq_id, NOT_APPLICABLE, SEQUENCE_NOT_IN_GFF, None))
    return issues


def fasta_gff_issues_to_df(issues):
    """
    Given dictionary of the issues for features, keyed by feature
    name, return a Pandas data frame with the issues. The data frame
    is sorted by sequence ID.

    The data frame has columns:

    * :py:const:`SEQUENCE`: sequence ID.
    * :py:const:`FEATURE`: feature ID.
    * :py:const:`ISSUE_TYPE`: issue type.
    * :py:const:`ISSUE_DATA`: issue data or ``None``.

    :param issues: List of issues for sequences and features.
    :type issues: list(tuple(str or unicode, str or unicode, \
    str or unicode, *))
    :return: data frame
    :rtype: pandas.core.frame.DataFrame
    """
    issues_list = []
    for (sequence_id, feature_id, issue_type, issue_data) in issues:
        issues_list.append({SEQUENCE: sequence_id,
                            FEATURE: feature_id,
                            ISSUE_TYPE: issue_type,
                            ISSUE_DATA: issue_data})
    # Create empty DataFrame so if issues and
    # issues_list are empty we still have an empty DataFrame
    # with the column names.
    df = pd.DataFrame(columns=[SEQUENCE, FEATURE, ISSUE_TYPE, ISSUE_DATA])
    df = df.append(pd.DataFrame(issues_list),
                   ignore_index=True)
    return df


def check_fasta_gff(fasta, gff, issues_file,
                    feature_format=CDS_FEATURE_FORMAT,
                    use_feature_name=False,
                    start_codons=[START_CODON],
                    delimiter="\t"):
    """
    Check FASTA and GFF files for compatibility and both print and
    save a list of issues for each sequence and coding sequence,
    ``CDS``, feature.

    A tab-separated values file of the issues identified is saved.

    See :py:func:`get_fasta_gff_cds_issues` for information on
    sequences, features, issue types and related data.

    See :py:func:`fasta_gff_issues_to_df` for tab-separated values
    file columns.

    :param fasta: FASTA file
    :type fasta: str or unicode
    :param gff: GFF file
    :type gff: str or unicode
    :param fasta: FASTA file
    :param issues_file: Feature issues file
    :type issues_file: str or unicode
    :param feature_format: Feature name format for features which \
    do not define ``ID``  or ``Name`` attributes. This format is \
    applied to the sequence ID to create a feature name.
    :type feature_format: str or unicode
    :param use_feature_name: If a feature defines both ``ID`` and \
    ``Name`` attributes then use ``Name` in reporting, otherwise use \
    ``ID``.
    :type use_feature_name: bool
    :param start_codons: Allowable start codons.
    :type start_codons: list(str or unicode)
    :param delimiter: Delimiter
    :type delimiter: str or unicode
    """
    issues = get_fasta_gff_cds_issues(fasta,
                                      gff,
                                      feature_format=feature_format,
                                      use_feature_name=use_feature_name,
                                      start_codons=start_codons)
    issues_df = fasta_gff_issues_to_df(issues)
    for _, row in issues_df.iterrows():
        issue = row[ISSUE_TYPE]
        if issue in ISSUE_FORMATS:
            print(ISSUE_FORMATS[issue].format(
                sequence=row[SEQUENCE],
                feature=row[FEATURE],
                data=row[ISSUE_DATA]))
    provenance.write_provenance_header(__file__, issues_file)
    issues_df[list(issues_df.columns)].to_csv(
        issues_file,
        mode='a',
        sep=delimiter,
        index=False)
