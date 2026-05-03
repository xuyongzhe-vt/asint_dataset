import os
from collections import Counter, defaultdict

def compare_dataset(our_family_asn_lists, their_family_asn_lists, asn_to_name, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    our_list = [[int(asn) for asn in cluster] for cluster in our_family_asn_lists]
    their_list = [[int(asn) for asn in cluster] for cluster in their_family_asn_lists]
    our_asns = set((asn for cluster in our_list for asn in cluster))
    their_asns = set((asn for cluster in their_list for asn in cluster))
    common_asns = our_asns & their_asns

    def filter_clusters(cluster_list):
        return [[asn for asn in cluster if asn in common_asns] for cluster in cluster_list if any((asn in common_asns for asn in cluster))]
    our_list_filtered = filter_clusters(our_list)
    their_list_filtered = filter_clusters(their_list)
    _assert_no_duplicates(our_list_filtered)
    _assert_no_duplicates(their_list_filtered)
    our_singletons = [set(c) for c in our_list_filtered if len(c) == 1]
    their_singletons = [set(c) for c in their_list_filtered if len(c) == 1]
    our_multi = [set(c) for c in our_list_filtered if len(c) > 1]
    their_multi = [set(c) for c in their_list_filtered if len(c) > 1]
    our_set = set((frozenset(c) for c in our_multi))
    their_set = set((frozenset(c) for c in their_multi))
    our_unique_clusters = [c for c in our_multi if frozenset(c) not in their_set]
    their_unique_clusters = [c for c in their_multi if frozenset(c) not in our_set]
    fully_covered_map = defaultdict(list)
    cover_counts_ours = {'multi': 0, 'single': 0}
    for our_cluster in our_unique_clusters:
        for their_cluster in their_unique_clusters:
            if their_cluster.issubset(our_cluster):
                cover_counts_ours['multi'] += 1
                fully_covered_map[frozenset(our_cluster)].append(their_cluster)
        for their_cluster in their_singletons:
            if their_cluster.issubset(our_cluster):
                cover_counts_ours['single'] += 1
                fully_covered_map[frozenset(our_cluster)].append(their_cluster)
    reverse_fully_covered_map = defaultdict(list)
    cover_counts_theirs = {'multi': 0, 'single': 0}
    for their_cluster in their_unique_clusters:
        for our_cluster in our_unique_clusters:
            if our_cluster.issubset(their_cluster):
                cover_counts_theirs['multi'] += 1
                reverse_fully_covered_map[frozenset(their_cluster)].append(our_cluster)
        for our_cluster in our_singletons:
            if our_cluster.issubset(their_cluster):
                cover_counts_theirs['single'] += 1
                reverse_fully_covered_map[frozenset(their_cluster)].append(our_cluster)
    involved_our = set(fully_covered_map.keys())
    for theirs in reverse_fully_covered_map.values():
        involved_our.update((frozenset(c) for c in theirs))
    involved_their = set(reverse_fully_covered_map.keys())
    for ours in fully_covered_map.values():
        involved_their.update((frozenset(c) for c in ours))
    remaining_our = [c for c in our_unique_clusters if frozenset(c) not in involved_our]
    remaining_their = [c for c in their_unique_clusters if frozenset(c) not in involved_their]
    asns_covered_by_ours = sum((len(c) for clusters in fully_covered_map.values() for c in clusters))
    asns_covered_by_theirs = sum((len(c) for clusters in reverse_fully_covered_map.values() for c in clusters))
    summary_path = os.path.join(output_dir, 'summary.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('==== Cluster Comparison Summary ====\n')
        f.write(f'Our clusters (after filter): {len(our_list_filtered)}\n')
        f.write(f'Their clusters (after filter): {len(their_list_filtered)}\n')
        f.write(f'Common ASNs: {len(common_asns)}\n')
        f.write(f'Singleton clusters (ours): {len(our_singletons)}\n')
        f.write(f'Singleton clusters (theirs): {len(their_singletons)}\n')
        f.write(f'Multi-member clusters (ours): {len(our_multi)}\n')
        f.write(f'Multi-member clusters (theirs): {len(their_multi)}\n\n')
        f.write(f'Identical multi-member clusters: {len(our_set & their_set)}\n')
        f.write(f'Our unique clusters (>1): {len(our_unique_clusters)}\n')
        f.write(f'Their unique clusters (>1): {len(their_unique_clusters)}\n')
        f.write(f"Our clusters fully covering theirs: {len(fully_covered_map)} (multi={cover_counts_ours['multi']}, single={cover_counts_ours['single']}, ASNs influenced={asns_covered_by_ours})\n")
        f.write(f"Their clusters fully covering ours: {len(reverse_fully_covered_map)} (multi={cover_counts_theirs['multi']}, single={cover_counts_theirs['single']}, ASNs influenced={asns_covered_by_theirs})\n")
        f.write(f'Remaining unmatched ours: {len(remaining_our)}\n')
        f.write(f'Remaining unmatched theirs: {len(remaining_their)}\n\n')
        f.write(f'Avg cluster size (ours, all): {_avg_size(our_list_filtered):.2f}\n')
        f.write(f'Avg cluster size (theirs, all): {_avg_size(their_list_filtered):.2f}\n')
        f.write('====================================\n')
    # _write_cover_file(os.path.join(output_dir, 'our_cover.txt'), fully_covered_map, asn_to_name, header_ours=True)
    # _write_cover_file(os.path.join(output_dir, 'reverse_cover.txt'), reverse_fully_covered_map, asn_to_name, header_ours=False)

def _assert_no_duplicates(cluster_list):
    seen = {}
    for cluster in cluster_list:
        for asn in cluster:
            assert asn not in seen, f'duplicate asn across clusters: {asn}'
            seen[asn] = 1

def _avg_size(clusters):
    if not clusters:
        return 0.0
    return sum((len(c) for c in clusters)) / len(clusters)

def _org_counts(asns, asn_to_name):
    counts = Counter()
    for asn in asns:
        counts[asn_to_name.get(asn, 'UNKNOWN')] += 1
    return counts

def _format_orgs(org_counts):
    items = sorted(org_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [f'{org} ({count})' for org, count in items]

def _write_cover_file(path, cover_map, asn_to_name, header_ours):
    outer_label = 'Our Cluster' if header_ours else 'Their Cluster'
    with open(path, 'w', encoding='utf-8') as f:
        for outer_cluster, inner_clusters in sorted(cover_map.items(), key=lambda kv: len(kv[0]), reverse=True):
            outer_asns = sorted(outer_cluster)
            outer_orgs = _format_orgs(_org_counts(outer_asns, asn_to_name))
            f.write('=' * 40 + '\n')
            f.write(f'=== {outer_label} ===\n')
            f.write(f'AS count: {len(outer_asns)}\n\n')
            f.write(f"Org names in {'our' if header_ours else 'their'} cluster:\n")
            for org_line in outer_orgs:
                f.write(f'  - {org_line}\n')
            f.write('\n-- Covers the following clusters --\n')
            for inner in sorted(inner_clusters, key=len, reverse=True):
                inner_asns = sorted(inner)
                inner_orgs = _format_orgs(_org_counts(inner_asns, asn_to_name))
                f.write(f'  • Covered cluster (AS count: {len(inner_asns)})\n')
                f.write('      Org names:\n')
                for org_line in inner_orgs:
                    f.write(f'        - {org_line}\n')
                f.write('\n')
            f.write('=' * 40 + '\n\n')
