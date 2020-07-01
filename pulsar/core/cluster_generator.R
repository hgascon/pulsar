
# reading arguments
cmd_args<- commandArgs(TRUE)
prisma_dir<-cmd_args[1]
capture_dir<-cmd_args[2]
clusters_file<-cmd_args[3]
nmf_ncomp<-cmd_args[4]
print(cmd_args)

# store the current directory
initial_dir<-getwd()

# load necessary libraries
# library(PRISMA)
library(Matrix)

# change to prisma src dir and load scripts
setwd(prisma_dir) 
source("prisma.R")
source("dimensionEstimation.R")
source("matrixFactorization.R") 
setwd(initial_dir)

# load the dataset
data = loadPrismaData(capture_dir)

# estimate number of components
#dim = calcEstimateDimension(data$unprocessed)
#cat("Estimated dimension:", estimateDimension(dim), "\n")
#ncomp = estimateDimension(dim)

dimension = estimateDimension(data)
ncomp <- dimension[[2]]
if (ncomp == 0) {
    ncomp <- strtoi(nmf_ncomp)
}
print (ncomp)
# find NMF decomposition
pmf = prismaNMF(data, ncomp)

#compute and write clusters to a file
clusters = calcDatacluster(pmf)

processed = filterDataByTestAndCor(data$unprocessed, 0.05, FALSE)
if (inherits(processed$mat, "Matrix")) {
    classes = calcClassForSparseMatrix(processed$mat)
}else {
    classes = sapply(1:ncol(processed$mat), function(colIndex) paste(which(processed$mat[, colIndex] == 1), collapse=" "))
}
classCount = table(classes)
uniqueClasses = names(classCount)
lines = sapply(names(data$remapper), function(x) colnames(data$data)[match(x, uniqueClasses)])
lineClusters = sapply(lines, function(x) clusters[match(x, names(clusters))])
names(lineClusters) = paste("line", 1:length(lineClusters), sep="")
write.table(lineClusters, clusters_file, row.names=FALSE, col.names=FALSE)
