# Findings: 5G Drop Rate Investigation

To: Network Director  
Re:Why 5G looks worse than 4G network-wide


The network-wide report shows that 5G has a higher drop rate than 4G (4.93% vs 3.21%). However, this aggregate result is misleading. When the data is broken down by region, 5G has a lower observed drop rate than 4G in all 7 regions where both technologies are deployed. This is an example of Simpson's paradox.

| Technology | Sessions | Drop rate |
|------------|---------:|----------:|
| 3G | 38,926 | 5.14% |
| 4G | 124,751 | 3.21% |
| 5G | 75,681 | 4.93% |

## Regional Comparison

| Region | 4G | 5G | Significant after correction? |
|--------|----:|----:|-------------------------------|
| Centre | 6.98% | 5.09% | Yes |
| Littoral | 7.86% | 5.67% | Yes |
| South-West | 3.32% | 2.43% | Yes |
| North-West | 2.89% | 1.74% | No |
| East | 2.11% | 1.39% | No |
| South | 2.13% | 1.27% | No |
| West | 3.02% | 2.83% | No |
| North | — | — | No 5G deployed |

5G has a lower observed drop rate than 4G in all 7 comparable regions. After Holm correction for multiple comparisons, the difference is statistically significant in 3 regions: Centre, Littoral, and South-West.

## Why the Reversal Happens

Centre and Littoral have relatively high drop rates for both technologies, while most of their traffic is on 5G. This means a large amount of 5G traffic comes from regions with higher baseline drop rates.

Because 4G and 5G are distributed differently across regions, combining all regions into one network-wide average can make 5G appear worse. Comparing the technologies within the same region gives a fairer comparison.

Combining performance across regions creates a false picture because 5G was deployed mainly in heavily overloaded regions where all calls drops more often.

Throughput: 5G has a median throughput of 41.44 Mbps compared with 26.78 Mbps for 4G, a difference of 14.66 Mbps. The bootstrap 95% confidence interval for the median difference was approximately 14.06–14.66 Mbps. A Mann-Whitney U test was used because throughput is strongly skewed.

## Recommendation

The network-wide drop-rate figure should not be interpreted on its own. Regional performance should be considered when evaluating the 5G rollout. Centre and Littoral should receive particular attention because both 4G and 5G show higher drop rates there.