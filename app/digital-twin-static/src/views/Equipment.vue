<template>
  <v-container grid-list-md >
    <v-layout row wrap >
      <v-flex xs4>
        <v-card>
          <v-card-media
            src="https://c1.staticflickr.com/8/7248/13806607764_411823213a_b.jpg"
            height="200px"
            ></v-card-media>

          <v-card-title primary-title>
            <div>
              <h3 class="headline mb-0">Multi Purpose Vessel</h3>
              <v-list dense>
                <v-list-tile>
                  <v-list-tile-content>Tonnage</v-list-tile-content>
                  <v-list-tile-content class="align-end">200</v-list-tile-content>
                </v-list-tile>
                <v-list-tile>
                  <v-list-tile-content>Speed</v-list-tile-content>
                  <v-list-tile-content class="align-end">11</v-list-tile-content>
                </v-list-tile>
                <v-list-tile>
                  <v-list-tile-content>Processing capacity</v-list-tile-content>
                  <v-list-tile-content class="align-end">3</v-list-tile-content>
                </v-list-tile>
              </v-list>
            </div>
          </v-card-title>

          <v-card-actions>
            <v-btn flat color="orange">Use</v-btn>
            <v-btn flat color="orange">Details</v-btn>
          </v-card-actions>
        </v-card>
      </v-flex>
      <v-flex xs4>
        <v-card>
          <v-card-media
            src="https://upload.wikimedia.org/wikipedia/commons/2/24/Dock_Crane%2C_Belfast_%286%29_-_geograph.org.uk_-_878924.jpg"
            height="200px"
            ></v-card-media>

          <v-card-title primary-title>
            <div>
              <h3 class="headline mb-0">Crane</h3>
              <v-list dense>
                <v-list-tile>
                  <v-list-tile-content>Processing capacity</v-list-tile-content>
                  <v-list-tile-content class="align-end">11</v-list-tile-content>
                </v-list-tile>
              </v-list>
            </div>
          </v-card-title>

          <v-card-actions>
            <v-btn flat color="orange">Use</v-btn>
            <v-btn flat color="orange">Details</v-btn>
          </v-card-actions>
        </v-card>
      </v-flex>
      <v-flex xs4>
        <v-card>
          <v-card-media
            src="https://upload.wikimedia.org/wikipedia/commons/6/60/Barge_%C3%A0_charbon.jpg"
            height="200px"
            ></v-card-media>

          <v-card-title primary-title>
            <div>
              <h3 class="headline mb-0">Barge</h3>
              <v-list dense>
                <v-list-tile>
                  <v-list-tile-content>Tonnage</v-list-tile-content>
                  <v-list-tile-content class="align-end">200</v-list-tile-content>
                </v-list-tile>
                <v-list-tile>
                  <v-list-tile-content>Speed</v-list-tile-content>
                  <v-list-tile-content class="align-end">11</v-list-tile-content>
                </v-list-tile>
              </v-list>
            </div>
          </v-card-title>

          <v-card-actions>
            <v-btn flat color="orange">Use</v-btn>
            <v-btn flat color="orange">Details</v-btn>
          </v-card-actions>
        </v-card>
      </v-flex>
    </v-layout>
  </v-container>

</template>

<script>
// @ is an alias to /src

export default {
  name: 'equipment',
  components: {
  }
}
</script>
