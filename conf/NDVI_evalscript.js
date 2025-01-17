//VERSION=3

//Based on https://custom-scripts.sentinel-hub.com/sentinel-2/max_ndvi/

function setup() {
    return {
        input: [{
            datasource: "s2",
            bands: ["B04", "B08", "SCL"],
        }],
        output: {
            id: "NDVI",
            bands: ["NDVI"],
            resx: 10,
            resy: 10,
            sampleType: "FLOAT32",
        },
        mosaicking: "ORBIT" //https://docs.sentinel-hub.com/api/latest/evalscript/v3/#mosaicking
    }
}


function validate(sample) {
    // See values in https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/scene-classification/
    return ![0, 1, 2, 3, 6, 7, 8, 9, 10].includes(sample.SCL)
}


function evaluatePixel(samples) {
    var max_ndvi = 0
    for (const sample of samples) {
        var isValid = validate(sample)

        if (isValid) {
            ndvi_value = index(sample.B08, sample.B04) // https://docs.sentinel-hub.com/api/latest/evalscript/functions/#index
            max_ndvi = ndvi_value > max_ndvi ? ndvi_value : max_ndvi
        }
    }
    return {NDVI: [max_ndvi]};
}