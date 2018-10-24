<template>
  <v-container>
    <v-stepper v-model="e1">
      <v-stepper-header>
        <v-stepper-step :complete="e1 > 1" step="1">Draw origins</v-stepper-step>

        <v-divider></v-divider>
        <v-stepper-step :complete="e1 > 2" step="2">Draw destinations</v-stepper-step>

        <v-divider></v-divider>

        <v-stepper-step :complete="e1 > 3" step="3">Configure sites</v-stepper-step>

        <v-divider></v-divider>

        <v-stepper-step :complete="e1 > 4" step="4">Select equipment</v-stepper-step>

        <v-divider></v-divider>

        <v-stepper-step step="5">Run activities</v-stepper-step>
      </v-stepper-header>

      <v-stepper-items>
        <v-stepper-content step="1">
          <v-card>
            <site-selection class="map" :site="origins"></site-selection>
          </v-card>

          <v-btn
            color="primary"
            @click="e1 = 2"
            >
            Next
          </v-btn>
        </v-stepper-content>
        <v-stepper-content step="2">
          <v-card>
            <site-selection class="map" :site="destination"></site-selection>
          </v-card>

          <v-btn
            color="primary"
            @click="e1 = 3"
            >
            Next
          </v-btn>
        </v-stepper-content>
        <v-stepper-content step="3">
          <v-card>
            <site-configuration :site="site"></site-configuration>
          </v-card>
          <v-btn
            color="primary"
            @click="e1 = 4"
            >
            Next
          </v-btn>
          <v-btn flat @click="e1=1">Back</v-btn>

        </v-stepper-content>

        <v-stepper-content step="4">
          <v-card>
            <equipment-selection class="equipment" :equipment="equipment"></equipment-selection>
          </v-card>

          <v-btn
            color="primary"
            @click="e1 = 5"
            >
            Next
          </v-btn>
          <v-btn flat @click="e1=3">Back</v-btn>

        </v-stepper-content>

        <v-stepper-content step="5">
          <v-card>
            <activity-runner :equipment="equipment" :site="site"></activity-runner>
          </v-card>
          <v-btn
            color="primary"
            @click="e1 = 1"
            >
            Done
          </v-btn>

          <v-btn flat @click="e1=4">Back</v-btn>
        </v-stepper-content>
      </v-stepper-items>
    </v-stepper>
  </v-container>

</template>
<style>
.map {
  height: 400px;
  width: 100%;
}
</style>
<script>
import SiteSelection from '@/components/SiteSelection.vue'
import SiteConfiguration from '@/components/SiteConfiguration.vue'
import EquipmentSelection from '@/components/EquipmentSelection.vue'
import ActivityRunner from '@/components/ActivityRunner.vue'

export default {
  name: 'wizard',
  data () {
    return {
      e1: 1,
      origins: {
        'features': {}
      },
      destination: {
        'features': {}
      },
      equipment: []
    }
  },
  computed: {
    site () {
      return {
        origins: this.origins,
        destination: this.destination
      }
    }
  },
  components: {
    'site-selection': SiteSelection,
    'site-configuration': SiteConfiguration,
    'equipment-selection': EquipmentSelection,
    'activity-runner': ActivityRunner
  }
}
</script>
