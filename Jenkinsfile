#!groovy
timestamps {
    node {
        try {
            checkout scm
            // Checkout submodules
			sh 'git rev-parse HEAD > commit'
			def gitRevision = readFile('commit').trim()
			echo "Revision: ${gitRevision}" 
            sh './project-setup.sh'
			buildImage("escape:2.0.0.${env.BUILD_NUMBER}", "--build-arg GIT_REVISION=${gitRevision} .")
			currentBuild.result = 'SUCCESS'
        } catch (any) {
			currentBuild.result = 'FAILURE'
			throw any
		} finally {
			step([$class: 'Mailer', recipients: '5gex-devel@tmit.bme.hu'])
		}
    }
}

def buildImage(String tag, String args = '.') {
    docker.withRegistry('https://5gex.tmit.bme.hu') {
        def image = docker.build(tag, args)
        image.push('unstable')
    }
}
