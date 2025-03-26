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
                id: "NDVI",
                bands: ["NDVI"],
                sampleType: "INT16",
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


function evaluatePixel(samples) {
    var ndvi_arr = []
    for (const sample of samples) {
        var isValid = validate(sample)

        // dataMask === 1 means there is data in that pixel
        if (isValid && (sample.dataMask === 1)) {
            ndvi_value = index(sample.B08, sample.B04) // https://docs.sentinel-hub.com/api/latest/evalscript/functions/#index
            ndvi_arr.push(ndvi_value)
        }
    }
    var ndvi = findMedian(ndvi_arr)
    ndvi = Math.round(ndvi * (2**16/2-1) ) // make result an integer because we are returning INT16 to save PUs, is reverted in the client
    return {NDVI: [ndvi]};
}