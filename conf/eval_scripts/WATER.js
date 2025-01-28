//VERSION=3

//Based on https://custom-scripts.sentinel-hub.com/sentinel-2/max_ndvi/

function setup() {
    return {
        input: [{
            datasource: "s2",
            bands: ["SCL", "dataMask"],
        }],
        output: [
            {
                id: "WATER",
                bands: ["WATER"],
                resx: 10,
                resy: 10,
                sampleType: "UINT8",
                nodataValue: 255
            }
        ],
        mosaicking: "ORBIT" //https://docs.sentinel-hub.com/api/latest/evalscript/v3/#mosaicking
    }
}


function validate(sample) {
    // See values in https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/scene-classification/
    return ![0, 1, 8, 9, 10].includes(sample.SCL)
}

function findAverage(arr) {
    const sum = arr.reduce((a, b) => a + b, 0);
    return (sum / arr.length) || 0;
}


function evaluatePixel(samples) {
    var is_water_arr = []
    for (const sample of samples) {
        var isValid = validate(sample)

        // dataMask === 1 means there is data in that pixel
        if (isValid && (sample.dataMask === 1)) {
            const is_water = sample.SCL === 6 ? 1 : 0
            is_water_arr.push(is_water)
        }
    }
    return {WATER: [Math.round(findAverage(is_water_arr))]};
}