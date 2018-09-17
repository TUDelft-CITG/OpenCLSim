<template>
  <v-container grid-list-md >
    <v-layout row wrap >
      <v-flex xs4 v-for="obj in equipment" :key="obj.id">
        <v-card>
          <v-card-media
            :src="obj.img"
            height="200px"
            ></v-card-media>

          <v-card-title primary-title>
            <div>
              <h3 class="headline mb-0">{{ obj.name }}</h3>
            </div>
          </v-card-title>
          <v-card-text>
            <v-list dense>
              <v-list-tile v-for="(val, key) in obj.properties" :key="key">
                <v-list-tile-content>{{ key }}</v-list-tile-content>
                <v-list-tile-content class="align-end">{{ val }}</v-list-tile-content>
              </v-list-tile>
            </v-list>
            <v-chip v-for="task in obj.tasks" :key="task.id">{{ task }}</v-chip>

          </v-card-text>

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
  data () {
    let equipment = [
      {
        id: 1,
        img: 'https://c1.staticflickr.com/8/7248/13806607764_411823213a_b.jpg',
        name: 'MVP-1',
        type: 'multi purpose vessel',
        tasks: ['mover', 'loader'],
        properties: {
          tonnage: 200,
          speed: 11,
          'processing capacity': 3
        }
      },
      {
        id: 2,
        name: 'Crane-1',
        img: 'https://upload.wikimedia.org/wikipedia/commons/2/24/Dock_Crane%2C_Belfast_%286%29_-_geograph.org.uk_-_878924.jpg',
        type: 'crane',
        tasks: ['loader'],
        properties: {
          'processing capacity': 3
        }
      },
      {
        id: 3,
        name: 'Barge-1',
        img: 'https://upload.wikimedia.org/wikipedia/commons/6/60/Barge_%C3%A0_charbon.jpg',
        type: 'barge',
        tasks: ['mover'],
        properties: {
          tonnage: 200,
          speed: 8
        }
      }
    ]
    return {
      equipment
    }
  },
  components: {
  }
}
</script>
