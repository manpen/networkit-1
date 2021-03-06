// networkit-format
#include <cassert>

#include <tlx/algorithm/random_bipartition_shuffle.hpp>
#include <networkit/graph/GraphTools.hpp>
#include <networkit/randomization/BipartiteGlobalCurveball.hpp>

#include <numeric>
#include <networkit/auxiliary/Random.hpp>

namespace NetworKit {

void BipartiteGlobalCurveball::compute_common_disjoint(std::vector<node> &neighbourhood_of_u,
                                                       std::vector<node> &neighbourhood_of_v,
                                                       std::vector<node> &common_neighbours,
                                                       std::vector<node> &disjoint_neighbours) {

    assert(common_neighbours.empty());
    assert(disjoint_neighbours.empty());

    // sort neighbourhoods to easily identify common neighbours
    // TODO: was machen wir mit dem vorsortieren?!?!
    // if (true){
    std::sort(neighbourhood_of_u.begin(), neighbourhood_of_u.end());
    std::sort(neighbourhood_of_v.begin(), neighbourhood_of_v.end());
    //}

    auto u_nit = neighbourhood_of_u.cbegin();
    auto v_nit = neighbourhood_of_v.cbegin();

    while ((u_nit != neighbourhood_of_u.cend()) && (v_nit != neighbourhood_of_v.cend())) {

        if (*u_nit > *v_nit) {
            disjoint_neighbours.push_back(*v_nit);
            v_nit++;
        } else if (*u_nit < *v_nit) {
            disjoint_neighbours.push_back(*u_nit);
            u_nit++;
        } else /* (*u_nit == *v_nit) */ {
            common_neighbours.push_back(*v_nit);
            u_nit++;
            v_nit++;
        }
    }

    // Append yet unprocessed neighbours (which have to be
    // disjoint since the trading partner has no more neighbours)
    if (u_nit != neighbourhood_of_u.cend()) {
        disjoint_neighbours.insert(disjoint_neighbours.end(), u_nit, neighbourhood_of_u.cend());
    } else {
        disjoint_neighbours.insert(disjoint_neighbours.end(), v_nit, neighbourhood_of_v.cend());
    }
}

void BipartiteGlobalCurveball::make_trade(std::vector<node> &common, std::vector<node> &disjoint,
                                          std::vector<node> &neighbourhood_of_u,
                                          std::vector<node> &neighbourhood_of_v,
                                          std::mt19937_64 &prng) {

    // u has to be the larger vector!

    if (neighbourhood_of_u.size() < neighbourhood_of_v.size()) {
        BipartiteGlobalCurveball::make_trade(common, disjoint, neighbourhood_of_v,
                                             neighbourhood_of_u, prng);
        return;
    }
    // tausche die Elemente in disjoint, aber nur so dass die erste partition zufällig ist, rest
    // egal
    const size_t partition_size = neighbourhood_of_v.size() - common.size();
    tlx::random_bipartition_shuffle(disjoint.begin(), disjoint.end(), partition_size, prng);

    // kopiere die gleichen elemente in u und v
    std::copy(common.begin(), common.end(), neighbourhood_of_u.begin());
    std::copy(common.begin(), common.end(), neighbourhood_of_v.begin());

    // u := large, v := small
    // Beginn nach common.size()
    // in v die ersten Elemente, der Rest in u
    std::copy(disjoint.begin(), disjoint.begin() + partition_size,
              neighbourhood_of_v.begin() + common.size());
    std::copy(disjoint.begin() + partition_size, disjoint.end(),
              neighbourhood_of_u.begin() + common.size());
}

void BipartiteGlobalCurveball::run(count numberOfGlobalTrades) {
    if (!hasRun) {
        // we may allow multiple calls to run(). In this case, we continue where we left,
        // which is useful if we want to take snapshots of the randomisation process;
        buildAdjList();
    }

    std::vector<node> perm;
    perm.resize(adjList.size());
    std::iota(perm.begin(), perm.end(), 0);

#pragma omp parallel
    {
        auto &prng = Aux::Random::getURNG();
        for (count round = 0; round < numberOfGlobalTrades; ++round) {

#pragma omp single
            { std::shuffle(perm.begin(), perm.end(), prng); };

            std::vector<node> common, disjoint;
            const auto maxDegree = NetworKit::GraphTools::maxDegree(inputGraph);

            disjoint.reserve(2 * maxDegree);
            common.reserve(2 * maxDegree);

            const auto n = static_cast<omp_index>(adjList.size() - 1);

#pragma omp for schedule(dynamic, 128)
            for (omp_index i = 0; i < n; i += 2) {
                common.clear();
                disjoint.clear();

                auto &u = adjList[perm[i]];
                auto &v = adjList[perm[i + 1]];

                BipartiteGlobalCurveball::compute_common_disjoint(u, v, common, disjoint);
                BipartiteGlobalCurveball::make_trade(common, disjoint, u, v, prng);
            }
        }
    }

    hasRun = true;
}

void BipartiteGlobalCurveball::buildAdjList() {
    assert(bipartitionClass.size() < inputGraph.numberOfNodes());
    adjList.reserve(bipartitionClass.size());

    for (node u : bipartitionClass) {
        assert(u < inputGraph.upperNodeIdBound());
        adjList.emplace_back();
        auto &current = adjList.back();

        current.resize(inputGraph.degree(u));
        auto range = inputGraph.neighborRange(u);
        std::copy(range.begin(), range.end(), current.begin());
    }
}

Graph BipartiteGlobalCurveball::getGraph() {
    Graph graph(inputGraph.numberOfNodes(), false, inputGraph.isDirected());

    if (inputGraph.isDirected()) {
        inputGraph.forNodes([&](node u) {
            graph.preallocateDirected(u, inputGraph.degreeOut(u), inputGraph.degreeIn(u));
        });
    } else {
        inputGraph.forNodes([&](node u) { graph.preallocateUndirected(u, inputGraph.degree(u)); });
    }

    node i = 0;
    for (const auto &vs : adjList) {
        const auto u = bipartitionClass[i++];
        for (auto v : vs) {
            graph.addEdge(u, v);
        }
    }
    return graph;
}

} // namespace NetworKit
