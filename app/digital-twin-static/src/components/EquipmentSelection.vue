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
            <v-chip v-for="tag in obj.tags" :key="tag">{{ tag }}</v-chip>

          </v-card-text>

          <v-card-actions>
            <v-btn flat @click="remove(obj)">Remove</v-btn>
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
  props: {
    equipment: Array
  },
  data () {
    return {}
  },
  mounted () {
    fetch('http://localhost:5000/equipment')
      .then(resp => {
        return resp.json()
      })
      .then(json => {
        this.equipment.push(...json)
      })
  },
  methods: {
    remove (obj) {
      const index = this.equipment.indexOf(obj)
      this.equipment.splice(index, 1)
    }
  },
  components: {
  }
}
</script>
