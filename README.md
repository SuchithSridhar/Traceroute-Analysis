# Traceroute Analysis

This is a python script to analyze the output of the command `traceroute`. It
plots a graph comparing distance to server and number hops and a graph comparing
distance to server and the time taken to travel (one-way).

**NOTE: This program is highly dependant on the output of `traceroute`.** Any
change, such as an extra space in the output, could break this program. Here is
the output of my `traceroute` program for which this program is based on. In
the case the program breaks due to this issue, updating the
`parse_traceroute_output` function should fix it.

```
❯ traceroute facebook.com      
traceroute to facebook.com (31.13.80.36), 30 hops max, 60 byte packets
 1  * * *
 2  * * *
 3  * * *
 4  ns-hlfx-br001.ns.eastlink.ca (24.215.101.221)  10.406 ms  10.387 ms  10.369 ms
 5  ns-hlfx-br002.ns.eastlink.ca (24.215.102.10)  11.368 ms  10.374 ms  10.353 ms
 6  facebook-b.ip4.torontointernetxchange.net (206.108.35.3)  87.265 ms ae42.pr01.yyz1.tfbnw.net (157.240.64.30)  206.983 ms  206.932 ms
 7  po101.psw03.yyz1.tfbnw.net (157.240.41.151)  206.913 ms po101.psw01.yyz1.tfbnw.net (157.240.41.147)  26.312 ms po103.psw02.yyz1.tfbnw.net (74.119.78.131)  28.696 ms
 8  157.240.38.185 (157.240.38.185)  28.679 ms 157.240.38.235 (157.240.38.235)  26.224 ms 173.252.67.171 (173.252.67.171)  26.197 ms
 9  edge-star-mini-shv-01-yyz1.facebook.com (31.13.80.36)  28.599 ms  28.575 ms  26.848 ms
```

## How to use

1. Ensure you have the `python` interpreter and `matplotlib` library installed.

2. Create an account on [IpStack](https://ipstack.com/) to obtain an API key
   which will be used to find the geolocation of a server.

3. Add your API key to a file named `ipstack-api-key.txt` with just your key in
   it.

4. Create a file with the coordinates (latitude and longitude) of your source
   machine named `source-location.txt`. Have the latitude and longitude comma
   separated. Example: `12.3515, 13.4562`. For best result use precise latitude
   and longitude values.
5. Run the program for a certain number of values, example: `python
   traceroute-script.py 10`. This will pick 10 random URLs from the
   `arch-mirror-list.txt` and perform `traceroute` on them.

6. View the results as either the generated CSV file or the two generated
   graphs. The files will be named `graph1.png`, `graph2.png`, and
   `output-table.csv`.


## References

1. The list of Arch Linux Mirrors is used
   https://wiki.archlinux.org/title/mirrors as a source of URLs since it has
   servers present all over the world. The list included in the repository was
   generated around 2023-09-09.

2. [IpStack](https://ipstack.com/) is used for it's API that can determine the
   geolocation of a particular IP Address. It's free to create an account.

3. https://www.movable-type.co.uk/scripts/latlong.html this URL was used as
   the formula to find the distance between two coordinates on Earth. It uses
   the 'haversine' formula.


## Conclusions On Experiment

Personally, I found that by running the script for a value of `300`, I found a
strong correlation between distance and time to reach but the correlation
between distance and number of hops seem to be pretty weak. There is some
correlation between distance and number of hops but it's not strong enough to
warrant any conclusion based on it. 

This experiment for my personal results was performed on a server sitting in
Halifax Nova Scotia, Canada. Here are the graphs from my experiment:

![Graph 1](./personal-results/graph1.png)

![Graph 2](./personal-results/graph2.png)
