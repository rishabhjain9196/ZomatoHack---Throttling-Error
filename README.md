# Workforce distribution using Demand-Supply HeatMap

> Second Runner's up of Zomato Hackanoodle Hackathon for Scale (2nd in Bangalore)

### Introuction
For applications like Uber/Ola/Rapdio/Zomato/Swiggy, the balance between the demand of resources (cab/bike/food) vs the suppliers of resources 
(cab drivers, riders, delivery systems) is key. This distriution aims to predict the distribution ahead of time and help the suppliers to move in where 
supply is supposed to be. Thus, creating a more balanced distribution. The suppliers are not forced to follow the decision - but are shown a probable heat-map on 
an android device. Post which they can take a conscious decision on the same. 


### Sample Heatmap distribution from a synthetic set of data on Bangalore Map
The darker the color (red > yellow > green) the more chances of getting a cab ride / food order from that area. <br>
<img src="https://github.com/rishabhjain9196/ZomatoHack---Throttling-Error/blob/master/documentation/b406b123-ea89-4276-8b14-3e2c8f8d2b19.jpeg" width="350"/>
<br>
<br>

### Key Components - 
#### Android Application
Shows heatmap as above
#### Backend - Django based
Cummalative location and heatmap updator
#### ML
LSTM based heat-map predictor

### Contributors (Team 7 - Throttling-Error):
- Abhirup Mondal
- Pooja Agarwal
- Rishabh Jain
- Sanket Jain
