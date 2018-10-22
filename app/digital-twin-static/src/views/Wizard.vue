<template>
  <v-container>
    <v-stepper v-model="e1">
      <v-stepper-header>
        <v-stepper-step :complete="e1 > 1" step="1">Draw site</v-stepper-step>

        <v-divider></v-divider>

        <v-stepper-step :complete="e1 > 2" step="2">Configure site</v-stepper-step>

        <v-divider></v-divider>

        <v-stepper-step :complete="e1 > 3" step="3">Select equipment</v-stepper-step>

        <v-divider></v-divider>

        <v-stepper-step step="4">Run activities</v-stepper-step>
      </v-stepper-header>

      <v-stepper-items>
        <v-stepper-content step="1">
          <v-card>
            <site-selection class="map" :site="site"></site-selection>
          </v-card>

          <v-btn
            color="primary"
            @click="e1 = 2"
            >
            Continue
          </v-btn>

          <v-btn flat>Cancel</v-btn>
        </v-stepper-content>

        <v-stepper-content step="2">
          <v-card>
            <site-configuration :site="site"></site-configuration>
          </v-card>
          <v-btn
            color="primary"
            @click="e1 = 3"
            >
            Continue
          </v-btn>

          <v-btn flat>Cancel</v-btn>
        </v-stepper-content>

        <v-stepper-content step="3">
          <v-card>
            <equipment-selection class="equipment"></equipment-selection>
          </v-card>

          <v-btn
            color="primary"
            @click="e1 = 4"
            >
            Continue
          </v-btn>

          <v-btn flat>Cancel</v-btn>
        </v-stepper-content>

        <v-stepper-content step="4">
          <v-card
            class="mb-5"
            color="grey lighten-1"
            height="200px"
            ></v-card>

          <v-btn
            color="primary"
            @click="e1 = 1"
            >
            Continue
          </v-btn>

          <v-btn flat>Cancel</v-btn>
        </v-stepper-content>
      </v-stepper-items>
    </v-stepper>
  </v-container>

</template>
<style>
.map {
  height: 500px;
  width: 100%;
}
</style>
<script>
import SiteSelection from '@/components/SiteSelection.vue'
import SiteConfiguration from '@/components/SiteConfiguration.vue'
import EquipmentSelection from '@/components/EquipmentSelection.vue'

export default {

  name: 'projects',
  data () {
    return {
      e1: 1,
      site: {}
    }
  },
  components: {
    'site-selection': SiteSelection,
    'site-configuration': SiteConfiguration,
    'equipment-selection': EquipmentSelection
  }
}
</script>
