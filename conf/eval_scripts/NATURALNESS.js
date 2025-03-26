//VERSION=3

//Based on https://custom-scripts.sentinel-hub.com/sentinel-2/max_ndvi/

function setup() {
    return {
        input: [{
            datasource: "s2",
            bands: ["B04", "B08", "SCL", "dataMask"],
        }],
        output: [
            {
                id: "NATURALNESS",
                bands: ["NATURALNESS"],
                sampleType: "UINT16",
                nodataValue: -999
            },
        ],
        mosaicking: "ORBIT" //https://docs.sentinel-hub.com/api/latest/evalscript/v3/#mosaicking
    }
}


function validate(sample) {
    // See values in https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/scene-classification/
    return ![0, 1, 8, 9, 10].includes(sample.SCL)
}


function findMedian(arr) {
    arr.sort((a, b) => a - b);
    const middleIndex = Math.floor(arr.length / 2);

    if (arr.length % 2 === 0) {
        return (arr[middleIndex - 1] + arr[middleIndex]) / 2;
    } else {
        return arr[middleIndex];
    }
}

function findAverage(arr) {
    const sum = arr.reduce((a, b) => a + b, 0);
    return (sum / arr.length) || 0;
}


function evaluatePixel(samples) {
    let ndvi_arr = []
    let is_water_arr = []
    for (const sample of samples) {
        let isValid = validate(sample)

        // dataMask === 1 means there is data in that pixel
        if (isValid && (sample.dataMask === 1)) {
            const is_water = sample.SCL === 6 ? 1 : 0
            is_water_arr.push(is_water)

            const ndvi_value = sample.SCL === 6 ? 1.0 : index(sample.B08, sample.B04) // https://docs.sentinel-hub.com/api/latest/evalscript/functions/#index
            ndvi_arr.push(ndvi_value)
        }
    }
    let naturalness = findAverage(is_water_arr) >= 0.5 ? 1.0 : findMedian(ndvi_arr)
    naturalness = naturalness < 0.0 ? 0.0 : naturalness
    naturalness = Math.round(naturalness * (2**16-1)) // make result an integer because we are returning INT16 to save PUs, is reverted in the client
    return {NATURALNESS: [naturalness]};
}