//VERSION=3

function setup() {
    return {
        input: [
            {
                datasource: "s2",
                bands: ["B04", "B08","SCL"],
        }],
        output: {
                id: "indice",
                bands: ["NDVI"],
                resx: 10,
                resy: 10,
                sampleType: "FLOAT32"
        },
        mosaicking: "ORBIT"
    }
}

function validate(samples) {
  var scl = samples.SCL

  if (scl === 3) {
    return false
  } else if (scl === 9) {
    return false
  } else if (scl === 8) {
    return false
  } else if (scl === 7) {
    return false
  } else if (scl === 10) {
    return false
  } else if (scl === 2) {
    return false
  }
  return true
}


function evaluatePixel(samples) {

    var ndvi_value
    var max = 0

    for (var i = 0; i < samples.length; i++) {
        var sample = samples[i]

        if (sample.B04 > 0 && sample.B08 > 0) {
            var isValid =  validate(sample)

            if (isValid) {
                ndvi_value = index(sample.B08, sample.B04)
                max = ndvi_value > max ? ndvi_value:max
            } else { ndvi_value = NaN }
        }
    }
  return {indice: [ndvi_value]}
}