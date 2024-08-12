// Function to create and display the bubble chart
function createBubbleChart(data) {
    console.log("Creating bubble chart with data:", data);

    const svgWidth = 800;
    const svgHeight = 600;
    const radiusScale = d3.scaleSqrt()
        .domain([0, d3.max(data, d => d.visitCount)])
        .range([0, 50]);

    d3.select("#bubbleChart").selectAll("*").remove();

    const svg = d3.select("#bubbleChart")
        .append("svg")
        .attr("width", svgWidth)
        .attr("height", svgHeight);

    const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

    const simulation = d3.forceSimulation(data)
        .force("x", d3.forceX(svgWidth / 2).strength(0.05))
        .force("y", d3.forceY(svgHeight / 2).strength(0.05))
        .force("collide", d3.forceCollide(d => radiusScale(d.visitCount) + 1))
        .on("tick", ticked);

    const node = svg.selectAll(".node")
        .data(data)
        .enter().append("g")
        .attr("class", "node")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    node.append("circle")
        .attr("r", d => radiusScale(d.visitCount))
        .style("fill", (d, i) => colorScale(i))
        .on("mouseover", function(event, d) {
            d3.select(this).style("stroke", "#000").style("stroke-width", "2px");
            d3.select("#tooltip").transition().duration(200).style("opacity", .9);
            d3.select("#tooltip").html(`<strong>Domain:</strong> ${d.domain}<br/><strong>Visit Count:</strong> ${d.visitCount}`)
                .style("left", (event.pageX + 5) + "px")
                .style("top", (event.pageY - 28) + "px");
        })
        .on("mouseout", function() {
            d3.select(this).style("stroke", null).style("stroke-width", null);
            d3.select("#tooltip").transition().duration(500).style("opacity", 0);
        })
        .on("contextmenu", function(event, d) {
            event.preventDefault();
            const contextMenu = d3.select("#contextMenu");
            contextMenu.style("display", "block")
                .style("left", (event.pageX + 5) + "px")
                .style("top", (event.pageY + 5) + "px");
            window.currentCellData = [d];
        });

    node.append("text")
        .attr("dy", ".3em")
        .attr("text-anchor", "middle")
        .style("font-size", "12px")
        .style("fill", "#fff")
        .text(d => {
            const domainParts = d.domain.split('.');
            if (d.visitCount > 50) {
                return d.domain;
            } else {
                const firstLetter = domainParts[0][0];
                const lastLetter = domainParts[0][domainParts[0].length - 1];
                return `${firstLetter}${lastLetter}`;
            }
        });

    function ticked() {
        node.select("circle")
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

        node.select("text")
            .attr("x", d => d.x)
            .attr("y", d => d.y);
    }

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    // Update the simulation with new data
    function updateSimulation(newData) {
        // Update the radius scale if necessary
        radiusScale.domain([0, d3.max(newData, d => d.visitCount)]);

        // Update the data for the nodes
        node.data(newData)
            .select("circle")
            .attr("r", d => radiusScale(d.visitCount));

        // Restart the simulation with the new data
        simulation.nodes(newData)
            .force("collide", d3.forceCollide(d => radiusScale(d.visitCount) + 1))
            .alpha(1)
            .restart();
    }

    // Event listener for date range sliders
    document.getElementById("fromDateRange").addEventListener("input", updateChart);
    document.getElementById("toDateRange").addEventListener("input", updateChart);

    function updateChart() {
        const fromDate = new Date(parseInt(document.getElementById("fromDateRange").value));
        const toDate = new Date(parseInt(document.getElementById("toDateRange").value));

        const filteredData = data.filter(d => {
            const visitDate = new Date(d.date);
            return visitDate >= fromDate && visitDate <= toDate;
        });

        // Filter out data points with visit count <= 10
        const filteredDataWithThreshold = filteredData.filter(d => d.visitCount > 10);

        // Update the simulation with the filtered data
        updateSimulation(filteredDataWithThreshold);
    }
}

// Event listener for document ready
document.addEventListener("DOMContentLoaded", function() {
    const toggleButton = document.getElementById("toggleBubbleChart");
    const heatmap = document.getElementById("heatmap");
    const bubbleChart = document.getElementById("bubbleChart");
    const controls = document.getElementById("bubbleChartControls");
    const fromDateRange = document.getElementById("fromDateRange");
    const toDateRange = document.getElementById("toDateRange");
    const fromDateLabel = document.getElementById("fromDateLabel");
    const toDateLabel = document.getElementById("toDateLabel");

    toggleButton.addEventListener("click", function() {
        if (bubbleChart.style.display === "none") {
            bubbleChart.style.display = "block";
            controls.style.display = "block";
            heatmap.style.display = "none";

            const csvData = sessionStorage.getItem('csvData');
            if (csvData) {
                const rows = d3.csvParse(csvData);
                const parseDate = d3.timeParse("%Y-%m-%d %H:%M:%S");
                let bubbleData = [];
                let minDate = Infinity;
                let maxDate = -Infinity;

                rows.forEach(row => {
                    const date = parseDate(row['date and time']);
                    if (date && date.getFullYear() > 2000) {
                        const domain = extractDomain(row['url']);
                        if (+row['visit count'] > 10) {  // Filter condition
                            bubbleData.push({ visitCount: +row['visit count'], domain: domain, url: row['url'], date: row['date and time'] });
                        }
                        if (date < minDate) minDate = date;
                        if (date > maxDate) maxDate = date;
                    }
                });

                fromDateRange.min = minDate.getTime();
                fromDateRange.max = maxDate.getTime();
                toDateRange.min = minDate.getTime();
                toDateRange.max = maxDate.getTime();
                fromDateRange.value = minDate.getTime();
                toDateRange.value = maxDate.getTime();

                fromDateLabel.textContent = minDate.toDateString();
                toDateLabel.textContent = maxDate.toDateString();

                createBubbleChart(bubbleData);
            } else {
                alert("No data found for bubble chart.");
            }
        } else {
            bubbleChart.style.display = "none";
            controls.style.display = "none";
        }
    });

    function extractDomain(url) {
        const parser = document.createElement('a');
        parser.href = url;
        return parser.hostname;
    }
});
